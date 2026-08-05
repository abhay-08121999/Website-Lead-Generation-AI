"""
google_places.py
-----------------
Primary lead-discovery source. Uses Google Places API (Text Search +
Place Details) to pull businesses per (city, category) combo.

Why Google Places as primary source:
- Structured, reliable JSON (no HTML parsing / breakage risk)
- Already tells us if a business HAS a listed website or not
  (the `website` field is simply absent for a huge chunk of SMBs)
- Gives phone, address, rating -> useful for lead prioritization later
"""

import time
import requests
from typing import List, Dict

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def search_businesses(city: str, category: str, api_key: str, max_results: int = 20) -> List[Dict]:
    """
    Search Google Places Text Search for a given category in a given city.
    Handles pagination (Google returns max 20 per page, up to 60 total
    via next_page_token).
    """
    query = f"{category} in {city}"
    params = {"query": query, "key": api_key}
    results = []

    while True:
        resp = requests.get(TEXT_SEARCH_URL, params=params, timeout=10)
        data = resp.json()

        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            print(f"  [WARN] Places API error for '{query}': {data.get('status')} - {data.get('error_message', '')}")
            break

        results.extend(data.get("results", []))

        next_token = data.get("next_page_token")
        if not next_token or len(results) >= max_results:
            break

        # Google requires a short delay before next_page_token becomes valid
        time.sleep(2)
        params = {"pagetoken": next_token, "key": api_key}

    return results[:max_results]


def get_place_details(place_id: str, api_key: str) -> Dict:
    """
    Fetch full details for a place (phone, website, address) using its
    place_id. Text Search alone doesn't always include `website`.
    """
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,formatted_phone_number,website,"
                   "international_phone_number,rating,user_ratings_total,business_status",
        "key": api_key,
    }
    resp = requests.get(DETAILS_URL, params=params, timeout=10)
    data = resp.json()

    if data.get("status") != "OK":
        return {}

    return data.get("result", {})


def discover_leads_for_city_category(city: str, category: str, api_key: str, max_results: int = 20) -> List[Dict]:
    """
    Full pipeline for one (city, category): search -> get details for
    each result -> normalize into a flat lead dict.
    """
    raw_results = search_businesses(city, category, api_key, max_results)
    leads = []

    for place in raw_results:
        place_id = place.get("place_id")
        if not place_id:
            continue

        details = get_place_details(place_id, api_key)
        if not details:
            continue

        leads.append({
            "business_name": details.get("name", place.get("name", "")),
            "city": city,
            "category": category,
            "address": details.get("formatted_address", ""),
            "phone": details.get("formatted_phone_number", ""),
            "rating": details.get("rating", ""),
            "review_count": details.get("user_ratings_total", ""),
            "website": details.get("website", ""),  # empty string = NO WEBSITE
            "business_status": details.get("business_status", ""),
            "source": "google_places",
        })

        time.sleep(0.2)  # gentle rate limiting

    return leads
