"""
justdial_scraper.py
--------------------
Secondary/supplementary lead source. Google Places is the reliable
backbone; this module fills gaps with very small, local businesses
that are listed on Justdial but not well-indexed on Google Maps.

IMPORTANT NOTES (read before using):
- Justdial actively runs anti-bot protection (WAF / JS challenges).
  This scraper is "best effort": it will work sometimes, get blocked
  other times. Don't rely on it as your only source.
- Always check Justdial's Terms of Service before scraping at scale.
  Keep request volume low and respect their robots.txt.
- If you consistently get blocked, consider Justdial's official
  Partner/API program instead of scraping.

This module fails *gracefully* — if a request gets blocked, it logs
a warning and returns an empty list rather than crashing the pipeline.
"""

import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
}

BASE_SEARCH_URL = "https://www.justdial.com/{city}/{category}"


def _slugify(text: str) -> str:
    return text.strip().replace(" ", "-")


def search_businesses(city: str, category: str, max_results: int = 20, delay: float = 1.5) -> List[Dict]:
    """
    Best-effort scrape of Justdial search results for a city+category.
    Returns a list of normalized lead dicts (may be empty if blocked).
    """
    url = BASE_SEARCH_URL.format(city=_slugify(city), category=_slugify(category))
    leads = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
    except requests.RequestException as e:
        print(f"  [WARN] Justdial request failed for {city}/{category}: {e}")
        return leads

    if resp.status_code != 200:
        print(f"  [WARN] Justdial returned status {resp.status_code} for {city}/{category} "
              f"(likely rate-limited or blocked). Skipping.")
        return leads

    soup = BeautifulSoup(resp.text, "lxml")

    # NOTE: Justdial's HTML structure changes frequently and is
    # obfuscated to deter scraping. The selectors below are a
    # starting point — inspect the live page and adjust class names
    # if they've changed by the time you run this.
    listing_cards = soup.select("div.resultbox_info, li.cntanr")

    if not listing_cards:
        print(f"  [INFO] No parsable listings found for {city}/{category} "
              f"(page structure may have changed, or JS-rendered content).")
        return leads

    for card in listing_cards[:max_results]:
        name_el = card.select_one("span.jcn, .resultbox_title")
        phone_el = card.select_one("span.callcontent, .contact-info")
        addr_el = card.select_one("span.mrehover, .resultbox_address")

        name = name_el.get_text(strip=True) if name_el else ""
        if not name:
            continue

        leads.append({
            "business_name": name,
            "city": city,
            "category": category,
            "address": addr_el.get_text(strip=True) if addr_el else "",
            "phone": phone_el.get_text(strip=True) if phone_el else "",
            "rating": "",
            "review_count": "",
            "website": "",  # Justdial listings for small businesses rarely show a website
            "business_status": "",
            "source": "justdial",
        })

    time.sleep(delay)
    return leads


def discover_leads_for_city_category(city: str, category: str, max_results: int = 20) -> List[Dict]:
    return search_businesses(city, category, max_results)
