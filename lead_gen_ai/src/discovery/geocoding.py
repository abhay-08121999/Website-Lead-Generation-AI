"""
geocoding.py
------------
Resolves a city name to a bounding box (south, west, north, east),
shared by both discovery modules (geoapify_places.py and the
osm_places.py fallback).

Lookup order:
1. config.CITY_BBOXES — hardcoded fast-path for the most common
   cities (instant, zero API calls).
2. In-memory cache — a city geocoded earlier in this process run.
3. Geoapify Geocoding API (same key as discovery) — dynamic lookup
   for any of the other 150+ cities in config.TARGET_CITIES, or any
   city a user types that isn't in the hardcoded list at all.

Using Geoapify (rather than Nominatim) for this fallback deliberately
avoids Nominatim's public rate-limits/403s on shared hosting IPs —
same reasoning as using Geoapify for discovery itself.
"""

import requests
from typing import Optional, Tuple

import config

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
HEADERS = {"User-Agent": "LeadScope/1.0 (student project)"}

_bbox_cache = {}


def get_city_bbox(city: str) -> Optional[Tuple[float, float, float, float]]:
    """Returns (south, west, north, east) or None if it can't be resolved."""
    if city in config.CITY_BBOXES:
        return config.CITY_BBOXES[city]

    if city in _bbox_cache:
        return _bbox_cache[city]

    if not config.GEOAPIFY_API_KEY:
        print(f"  [WARN] '{city}' has no hardcoded bbox and GEOAPIFY_API_KEY is not set — cannot geocode.", flush=True)
        return None

    params = {
        "text": f"{city}, India",
        "type": "city",
        "format": "json",
        "limit": 1,
        "apiKey": config.GEOAPIFY_API_KEY,
    }

    try:
        resp = requests.get(GEOCODE_URL, params=params, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        print(f"  [WARN] Geoapify geocoding failed for '{city}': {e}", flush=True)
        return None

    if resp.status_code != 200:
        print(f"  [WARN] Geoapify geocoding returned status {resp.status_code} for '{city}'", flush=True)
        return None

    try:
        data = resp.json()
    except ValueError:
        print(f"  [WARN] Geoapify geocoding returned non-JSON for '{city}'", flush=True)
        return None

    results = data.get("results", data.get("features", []))
    if not results:
        print(f"  [WARN] Geoapify found no match for city '{city}'", flush=True)
        return None

    first = results[0]
    # format=json gives flat objects; GeoJSON gives {"properties": {...}}
    props = first.get("properties", first)
    bbox = props.get("bbox")

    if not bbox:
        print(f"  [WARN] Geoapify result for '{city}' had no bbox — geocoding too imprecise to use.", flush=True)
        return None

    try:
        if isinstance(bbox, dict):
            south, west, north, east = bbox["lat1"], bbox["lon1"], bbox["lat2"], bbox["lon2"]
            south, north = min(south, north), max(south, north)
            west, east = min(west, east), max(west, east)
        else:  # list format [west, south, east, north]
            west, south, east, north = bbox
    except (KeyError, ValueError, TypeError):
        print(f"  [WARN] Could not parse bbox format for '{city}': {bbox}", flush=True)
        return None

    bbox_tuple = (south, west, north, east)
    _bbox_cache[city] = bbox_tuple
    print(f"  [INFO] Geocoded '{city}' dynamically via Geoapify", flush=True)
    return bbox_tuple
