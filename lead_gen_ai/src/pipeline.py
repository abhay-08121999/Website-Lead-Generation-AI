"""
pipeline.py
-----------
Core discover -> analyze -> score pipeline, extracted so both the
CLI (main.py) and the Flask web app (app.py) can call the exact same
logic without duplicating code.
"""

import time
from typing import List, Dict

import config
from src.discovery import osm_places, justdial_scraper
from src.analysis import website_checker, performance_analyzer
from src.scoring import lead_scorer


def discover_all(cities: List[str], categories: List[str], max_results: int, use_justdial: bool = True) -> List[Dict]:
    all_businesses = []
    for city in cities:
        for category in categories:
            print(f"[DISCOVER] {category} in {city} ...")

            try:
                osm_leads = osm_places.discover_leads_for_city_category(city, category, max_results)
                print(f"  -> OpenStreetMap: {len(osm_leads)} businesses")
                all_businesses.extend(osm_leads)
            except Exception as e:
                print(f"  [ERROR] OpenStreetMap discovery failed for {city}/{category}: {e}")

            if use_justdial:
                try:
                    jd_leads = justdial_scraper.discover_leads_for_city_category(city, category, max_results)
                    print(f"  -> Justdial: {len(jd_leads)} businesses")
                    all_businesses.extend(jd_leads)
                except Exception as e:
                    print(f"  [ERROR] Justdial failed for {city}/{category}: {e}")

    return all_businesses


def deduplicate(businesses: List[Dict]) -> List[Dict]:
    """Remove duplicate businesses (same name + city, case-insensitive)."""
    seen = set()
    unique = []
    for b in businesses:
        key = (b.get("business_name", "").strip().lower(), b.get("city", "").strip().lower())
        if key not in seen and key[0]:
            seen.add(key)
            unique.append(b)
    return unique


def analyze_and_score(businesses: List[Dict], run_performance_check: bool = True) -> List[Dict]:
    scored = []
    for i, biz in enumerate(businesses, 1):
        website = biz.get("website", "").strip()
        print(f"[{i}/{len(businesses)}] Analyzing: {biz.get('business_name')} ({biz.get('city')})")

        if not website:
            scored.append(lead_scorer.score_lead(biz))
            continue

        health = website_checker.check_website_health(website)
        perf = {}
        if run_performance_check and config.PAGESPEED_API_KEY and health.get("reachable") and not health.get("is_placeholder"):
            perf = performance_analyzer.analyze_performance(website, config.PAGESPEED_API_KEY)
            time.sleep(config.REQUEST_DELAY)

        scored.append(lead_scorer.score_lead(biz, health, perf))

    return scored


def run_full_pipeline(cities: List[str], categories: List[str], max_results: int,
                       use_justdial: bool = True, run_performance: bool = True) -> List[Dict]:
    """
    Full end-to-end pipeline: discover -> dedup -> analyze -> score ->
    filter to qualified leads only. Returns the qualified leads list
    (does NOT export to Excel — caller decides what to do with results).
    """
    businesses = discover_all(cities, categories, max_results, use_justdial)
    print(f"\n[TOTAL DISCOVERED] {len(businesses)} businesses (before dedup)")

    businesses = deduplicate(businesses)
    print(f"[AFTER DEDUP] {len(businesses)} unique businesses\n")

    scored = analyze_and_score(businesses, run_performance_check=run_performance)

    qualified = [s for s in scored if lead_scorer.is_qualified_lead(s)]
    print(f"\n[QUALIFIED LEADS] {len(qualified)} out of {len(scored)} businesses")

    return qualified
