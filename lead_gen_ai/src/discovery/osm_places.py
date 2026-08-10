"""
osm_places.py
-------------
FREE discovery source — no API key, no billing, no card required.
Uses OpenStreetMap's Overpass API to find businesses by city + category.

Approach:
1. Geocode the city name once via Nominatim -> get a bounding box
   (south, west, north, east). This is MUCH faster than asking
   Overpass to search by administrative area name, which requires
   scanning the whole boundary dataset and often times out (504) on
   the shared public server.
2. Query Overpass for businesses within that bounding box, matching
   the category's OSM tags.
3. Try multiple public Overpass mirrors in order — the shared public
   instances occasionally get overloaded, so we fail over instead of
   giving up on the first timeout.

Trade-off vs Google Places:
- No cost, no signup friction.
- Data is community-maintained, so coverage/completeness varies by
  city (metros are generally well-mapped; smaller towns may be sparse).
- No ratings/review counts (OSM doesn't track those).
- `website`/`phone` tags exist for a good chunk of businesses but not
  all — missing tag = no website = still a clean "hot lead" signal.

Usage policy: be gentle (see config delays), send an identifying
User-Agent, don't hammer the public servers.
"""

import time
import requests
from typing import List, Dict, Optional, Tuple

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config

HEADERS = {"User-Agent": config.OSM_USER_AGENT}

# Cache city -> bounding box so we only geocode each city once per run
_city_bbox_cache = {}


def geocode_city(city: str) -> Optional[Tuple[float, float, float, float]]:
    """
    Resolves a city name to a bounding box (south, west, north, east).

    1. Check the hardcoded config.CITY_BBOXES dict first (instant,
       no network call, no dependency on Nominatim's availability).
    2. Fall back to live Nominatim geocoding only for cities not in
       that dict (e.g. if the user passes --city for somewhere new).
    """
    if city in config.CITY_BBOXES:
        return config.CITY_BBOXES[city]

    if city in _city_bbox_cache:
        return _city_bbox_cache[city]

    print(f"  [INFO] '{city}' not in hardcoded city list — trying live geocoding via Nominatim...", flush=True)

    params = {
        "city": city,
        "country": "India",
        "format": "json",
        "limit": 1,
    }

    try:
        resp = requests.get(config.NOMINATIM_URL, params=params, headers=HEADERS, timeout=15)
        time.sleep(config.NOMINATIM_REQUEST_DELAY)
    except requests.RequestException as e:
        print(f"  [WARN] Nominatim geocoding failed for '{city}': {e}", flush=True)
        return None

    if resp.status_code != 200:
        print(f"  [WARN] Nominatim returned status {resp.status_code} for '{city}'. "
              f"Tip: add '{city}' to CITY_BBOXES in config.py to skip geocoding entirely.", flush=True)
        return None

    try:
        results = resp.json()
    except ValueError:
        print(f"  [WARN] Nominatim returned non-JSON response for '{city}'", flush=True)
        return None

    if not results:
        print(f"  [WARN] Nominatim found no match for city '{city}'", flush=True)
        return None

    bbox = results[0].get("boundingbox")  # [south, north, west, east] as strings
    if not bbox or len(bbox) != 4:
        return None

    south, north, west, east = (float(v) for v in bbox)
    bbox_tuple = (south, west, north, east)
    _city_bbox_cache[city] = bbox_tuple
    return bbox_tuple


def _build_query(bbox: Tuple[float, float, float, float], tag_pairs: List[tuple], limit: int) -> str:
    """Builds an Overpass QL query scoped to a bounding box (fast)."""
    south, west, north, east = bbox
    bbox_str = f"{south},{west},{north},{east}"

    clauses = []
    for key, value in tag_pairs:
        clauses.append(f'  node["{key}"="{value}"]({bbox_str});')
        clauses.append(f'  way["{key}"="{value}"]({bbox_str});')

    clause_block = "\n".join(clauses)

    query = f"""
[out:json][timeout:{config.OVERPASS_TIMEOUT_SECONDS}];
(
{clause_block}
);
out center {limit * 2};
"""
    return query.strip()


def _query_overpass(query: str) -> Optional[Dict]:
    """
    Tries each configured Overpass mirror in order. If ALL mirrors
    fail on the first pass (common with shared rate limits on public
    servers), waits and does one full retry pass before giving up —
    transient 429s/504s often clear within a few seconds.
    """
    for attempt in range(2):
        for url in config.OVERPASS_URLS:
            try:
                resp = requests.post(url, data={"data": query}, headers=HEADERS,
                                      timeout=config.OVERPASS_TIMEOUT_SECONDS + 5)
            except requests.RequestException as e:
                print(f"  [WARN] Overpass mirror {url} failed: {e} — trying next mirror...", flush=True)
                continue

            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    print(f"  [WARN] Overpass mirror {url} returned non-JSON — trying next mirror...", flush=True)
                    continue

            if resp.status_code == 429:
                print(f"  [WARN] Overpass mirror {url} rate-limited us — trying next mirror...", flush=True)
            else:
                print(f"  [WARN] Overpass mirror {url} returned status {resp.status_code} — trying next mirror...", flush=True)

        if attempt == 0:
            print("  [INFO] All mirrors failed on first pass — waiting 10s before one retry pass...", flush=True)
            time.sleep(10)

    return None


def _extract_lead(element: Dict, city: str, category: str) -> Dict:
    tags = element.get("tags", {})
    name = tags.get("name", "")
    if not name:
        return {}

    addr_parts = [
        tags.get("addr:housenumber", ""),
        tags.get("addr:street", ""),
        tags.get("addr:suburb", ""),
        tags.get("addr:city", ""),
    ]
    address = ", ".join(p for p in addr_parts if p)

    website = tags.get("website") or tags.get("contact:website") or ""
    phone = tags.get("phone") or tags.get("contact:phone") or ""

    return {
        "business_name": name,
        "city": city,
        "category": category,
        "address": address,
        "phone": phone,
        "rating": "",
        "review_count": "",
        "website": website,
        "business_status": "",
        "source": "openstreetmap",
    }


def discover_leads_for_city_category(city: str, category: str, max_results: int = 20) -> List[Dict]:
    """
    Full pipeline for one (city, category): geocode city -> query
    Overpass (with mirror fallback) -> parse -> normalize. Fails
    gracefully (returns []) so one bad city/category doesn't kill
    the whole run.
    """
    tag_pairs = config.OSM_CATEGORY_TAGS.get(category)
    if not tag_pairs:
        print(f"  [WARN] No OSM tag mapping for category '{category}' — skipping.", flush=True)
        return []

    bbox = geocode_city(city)
    if not bbox:
        print(f"  [WARN] Could not resolve bounding box for '{city}' — skipping.", flush=True)
        return []

    query = _build_query(bbox, tag_pairs, max_results)
    data = _query_overpass(query)

    if data is None:
        print(f"  [WARN] All Overpass mirrors failed for {city}/{category}.", flush=True)
        return []

    elements = data.get("elements", [])
    leads = []
    for el in elements:
        lead = _extract_lead(el, city, category)
        if lead:
            leads.append(lead)
        if len(leads) >= max_results:
            break

    time.sleep(config.OVERPASS_REQUEST_DELAY)
    return leads
