"""
here_places.py
---------------
SECONDARY discovery source — runs alongside Geoapify (not a fallback,
a genuinely different, proprietary POI database). HERE maintains its
own map data (not OpenStreetMap), so it can surface businesses that
Geoapify/OSM don't have mapped, and vice versa — combining both
widens overall coverage.

Uses the /discover endpoint (free-text search) rather than /browse
with category codes — HERE's numeric category taxonomy isn't fully
documented publicly, so free-text search terms (config.HERE_SEARCH_TERMS)
are far more reliable than guessing at category IDs.

Free tier ("Limited Plan"): 1,000 requests/day, NO credit card
required. Get a key: https://platform.here.com/

Docs: https://www.here.com/docs/bundle/geocoding-and-search-api-developer-guide/page/topics/endpoint-discover-brief.html
"""

import requests
from typing import List, Dict

import config
from src.discovery.geocoding import get_city_bbox

DISCOVER_URL = "https://discover.search.hereapi.com/v1/discover"


def _extract_field(item: Dict, contact_type: str) -> str:
    """
    HERE returns contact info as a list of typed entries, e.g.:
    "contacts": [{"phone": [{"value": "..."}], "www": [{"value": "..."}]}]
    """
    contacts = item.get("contacts", [])
    for entry in contacts:
        values = entry.get(contact_type)
        if values:
            return values[0].get("value", "")
    return ""


def discover_leads_for_city_category(city: str, category: str, max_results: int = 20) -> List[Dict]:
    """
    Full pipeline for one (city, category): geocode city -> query HERE
    Discover with a free-text search term scoped to the bounding box
    -> normalize into flat lead dicts. Fails gracefully (returns [])
    so one bad city/category doesn't kill the whole run.
    """
    if not config.HERE_API_KEY:
        return []  # silent — this is a secondary/optional source, not a hard requirement

    search_term = config.HERE_SEARCH_TERMS.get(category)
    if not search_term:
        return []

    bbox = get_city_bbox(city)
    if not bbox:
        return []

    south, west, north, east = bbox
    # HERE's "in=bbox:" format is west,south,east,north (same convention as Geoapify's rect)
    bbox_str = f"{west},{south},{east},{north}"

    params = {
        "q": search_term,
        "in": f"bbox:{bbox_str}",
        "limit": min(max_results, 100),
        "apiKey": config.HERE_API_KEY,
    }

    try:
        resp = requests.get(DISCOVER_URL, params=params, timeout=15)
    except requests.RequestException as e:
        print(f"  [WARN] HERE request failed for {city}/{category}: {e}", flush=True)
        return []

    if resp.status_code != 200:
        print(f"  [WARN] HERE returned status {resp.status_code} for {city}/{category}: {resp.text[:200]}", flush=True)
        return []

    try:
        data = resp.json()
    except ValueError:
        print(f"  [WARN] HERE returned non-JSON response for {city}/{category}", flush=True)
        return []

    items = data.get("items", [])
    leads = []

    for item in items:
        name = item.get("title", "")
        if not name:
            continue

        address = item.get("address", {})

        leads.append({
            "business_name": name,
            "city": city,
            "category": category,
            "address": address.get("label", ""),
            "phone": _extract_field(item, "phone"),
            "rating": "",
            "review_count": "",
            "website": _extract_field(item, "www"),
            "business_status": "",
            "source": "here",
        })

    return leads
