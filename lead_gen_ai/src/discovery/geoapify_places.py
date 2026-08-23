"""
geoapify_places.py
-------------------
PRIMARY discovery source — Geoapify Places API.

Requests go to Geoapify's own dedicated infrastructure, not the
shared public Overpass mirrors — those reject connections from many
cloud-hosting IP ranges (Render's included), causing silent 0-result
discovery in production even though everything works fine locally.

Free tier: 3,000 requests/day, no credit card required.
Docs: https://apidocs.geoapify.com/docs/places/
"""

import requests
from typing import List, Dict

import config
from src.discovery.geocoding import get_city_bbox

PLACES_URL = "https://api.geoapify.com/v2/places"


def _extract_contact_field(props: Dict, field: str) -> str:
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
    if not config.GEOAPIFY_API_KEY:
        print("  [WARN] GEOAPIFY_API_KEY not set — cannot discover businesses.", flush=True)
        return []

    geo_category = config.GEOAPIFY_CATEGORY_MAP.get(category)
    if not geo_category:
        print(f"  [WARN] No Geoapify category mapping for '{category}' — skipping.", flush=True)
        return []

    bbox = get_city_bbox(city)
    if not bbox:
        print(f"  [WARN] Could not resolve bounding box for '{city}' — skipping.", flush=True)
        return []

    south, west, north, east = bbox
    rect = f"{west},{south},{east},{north}"

    # Request a small buffer above what's needed — even with the
    # "named" condition filtering server-side, Geoapify occasionally
    # includes entries with only a generic/empty display name that
    # still get skipped client-side below. The buffer compensates so
    # we're more likely to hit the caller's requested count.
    request_limit = min(max_results + 10, 200)

    params = {
        "categories": geo_category,
        "conditions": "named",  # server-side filter: only places with a real name set
        "filter": f"rect:{rect}",
        "limit": request_limit,
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
        if len(leads) >= max_results:
            break

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
