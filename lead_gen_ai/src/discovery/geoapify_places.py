"""
geoapify_places.py
-------------------
PRIMARY discovery source — Geoapify Places API.

Why Geoapify instead of calling Overpass directly:
- Same underlying data (OpenStreetMap), so coverage/accuracy is
  unchanged from before.
- Requests go to Geoapify's own dedicated infrastructure, not the
  shared public overpass-api.de/mirrors — those public mirrors
  actively reject connections from many cloud-hosting IP ranges
  (Render's included), causing silent 0-result discovery in
  production even though everything works fine locally.
- Free tier: 3,000 requests/day, no credit card required.
  Get a key: https://myprojects.geoapify.com/

Docs: https://apidocs.geoapify.com/docs/places/
"""

import requests
from typing import List, Dict

import config

PLACES_URL = "https://api.geoapify.com/v2/places"


def _extract_contact_field(props: Dict, field: str) -> str:
    """
    Geoapify sometimes puts contact info as a top-level property,
    sometimes nested under 'contact', and sometimes only in the raw
    OSM tags under 'datasource.raw'. Check all three, in that order.
    """
    if props.get(field):
        return props[field]

    contact = props.get("contact")
    if isinstance(contact, dict) and contact.get(field):
        return contact[field]

    raw = props.get("datasource", {}).get("raw", {})
    if isinstance(raw, dict):
        return raw.get(field) or raw.get(f"contact:{field}") or ""

    return ""


def discover_leads_for_city_category(city: str, category: str, max_results: int = 20) -> List[Dict]:
    """
    Full pipeline for one (city, category): map to Geoapify category
    -> query Places API -> normalize into flat lead dicts. Fails
    gracefully (returns []) so one bad city/category doesn't kill
    the whole run.
    """
    if not config.GEOAPIFY_API_KEY:
        print("  [WARN] GEOAPIFY_API_KEY not set — cannot discover businesses.", flush=True)
        return []

    geo_category = config.GEOAPIFY_CATEGORY_MAP.get(category)
    if not geo_category:
        print(f"  [WARN] No Geoapify category mapping for '{category}' — skipping.", flush=True)
        return []

    bbox = config.CITY_BBOXES.get(city)
    if not bbox:
        print(f"  [WARN] No bounding box configured for '{city}' — skipping.", flush=True)
        return []

    south, west, north, east = bbox
    # Geoapify rect filter format is "rect:lon1,lat1,lon2,lat2" i.e. west,south,east,north
    rect = f"{west},{south},{east},{north}"

    params = {
        "categories": geo_category,
        "filter": f"rect:{rect}",
        "limit": max_results,
        "apiKey": config.GEOAPIFY_API_KEY,
    }

    try:
        resp = requests.get(PLACES_URL, params=params, timeout=20)
    except requests.RequestException as e:
        print(f"  [WARN] Geoapify request failed for {city}/{category}: {e}", flush=True)
        return []

    if resp.status_code != 200:
        print(f"  [WARN] Geoapify returned status {resp.status_code} for {city}/{category}: {resp.text[:200]}", flush=True)
        return []

    try:
        data = resp.json()
    except ValueError:
        print(f"  [WARN] Geoapify returned non-JSON response for {city}/{category}", flush=True)
        return []

    features = data.get("features", [])
    leads = []

    for feature in features:
        props = feature.get("properties", {})
        name = props.get("name", "")
        if not name:
            continue

        leads.append({
            "business_name": name,
            "city": city,
            "category": category,
            "address": props.get("formatted", "") or props.get("address_line2", ""),
            "phone": _extract_contact_field(props, "phone"),
            "rating": "",
            "review_count": "",
            "website": _extract_contact_field(props, "website"),
            "business_status": "",
            "source": "geoapify",
        })

    return leads
