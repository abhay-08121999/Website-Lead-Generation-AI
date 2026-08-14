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
from src.discovery import geoapify_places, osm_places
from src.analysis import (
    website_checker, performance_analyzer,
    wayback_checker, domain_checker, crux_checker, safe_browsing_checker,
)
from src.scoring import lead_scorer


def discover_all(cities: List[str], categories: List[str], max_results: int) -> List[Dict]:
    all_businesses = []
    for city in cities:
        for category in categories:
            print(f"[DISCOVER] {category} in {city} ...", flush=True)

            leads = []
            try:
                leads = geoapify_places.discover_leads_for_city_category(city, category, max_results)
                print(f"  -> Geoapify: {len(leads)} businesses", flush=True)
            except Exception as e:
                print(f"  [ERROR] Geoapify discovery failed for {city}/{category}: {e}", flush=True)

            # Fallback to direct Overpass only if Geoapify returned nothing
            # (e.g. no key configured, or a transient API issue) — keeps
            # the pipeline working even without a Geoapify key.
            if not leads:
                try:
                    osm_leads = osm_places.discover_leads_for_city_category(city, category, max_results)
                    print(f"  -> OpenStreetMap (fallback): {len(osm_leads)} businesses", flush=True)
                    leads = osm_leads
                except Exception as e:
                    print(f"  [ERROR] OpenStreetMap fallback failed for {city}/{category}: {e}", flush=True)

            all_businesses.extend(leads)

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
        print(f"[{i}/{len(businesses)}] Analyzing: {biz.get('business_name')} ({biz.get('city')})", flush=True)

        if not website:
            scored.append(lead_scorer.score_lead(biz))
            continue

        health = website_checker.check_website_health(website)

        # If the site is dead or a placeholder, no point running the
        # remaining (slower/rate-limited) checks — it's already a lead.
        if not health.get("reachable") or health.get("is_placeholder"):
            scored.append(lead_scorer.score_lead(biz, health))
            continue

        perf, wayback, domain, crux, safe_browsing = {}, {}, {}, {}, {}

        if run_performance_check and config.PAGESPEED_API_KEY:
            perf = performance_analyzer.analyze_performance(website, config.PAGESPEED_API_KEY)
            if perf.get("error"):
                print(f"  [WARN] PageSpeed check failed for {website}: {perf['error']}", flush=True)
            elif perf.get("performance_score") is not None:
                print(f"  [INFO] PageSpeed score for {website}: {perf['performance_score']}/100", flush=True)
            time.sleep(config.REQUEST_DELAY)

        wayback = wayback_checker.check_last_updated(website)
        if wayback.get("error"):
            print(f"  [WARN] Wayback check failed for {website}: {wayback['error']}", flush=True)
        elif wayback.get("is_stale"):
            print(f"  [INFO] {website} last changed {wayback.get('last_snapshot_date')} — stale", flush=True)

        domain = domain_checker.check_domain_expiry(website)
        if domain.get("error"):
            print(f"  [WARN] Domain check failed for {website}: {domain['error']}", flush=True)
        elif domain.get("is_expiring_soon") or domain.get("is_expired"):
            print(f"  [INFO] {website} domain expiry: {domain.get('expiry_date')}", flush=True)

        if config.PAGESPEED_API_KEY:  # CrUX and Safe Browsing use the same Google API key
            crux = crux_checker.check_crux(website, config.PAGESPEED_API_KEY)
            if crux.get("error"):
                print(f"  [WARN] CrUX check failed for {website}: {crux['error']}", flush=True)

            safe_browsing = safe_browsing_checker.check_safe_browsing(website, config.PAGESPEED_API_KEY)
            if safe_browsing.get("error"):
                print(f"  [WARN] Safe Browsing check failed for {website}: {safe_browsing['error']}", flush=True)
            elif safe_browsing.get("is_flagged"):
                print(f"  [WARN] {website} flagged by Safe Browsing!", flush=True)

        scored.append(lead_scorer.score_lead(biz, health, perf, wayback, domain, crux, safe_browsing))

    return scored


def run_full_pipeline(cities: List[str], categories: List[str], max_results: int,
                       run_performance: bool = True) -> List[Dict]:
    """
    Full end-to-end pipeline: discover -> dedup -> analyze -> score ->
    filter to qualified leads only. Returns the qualified leads list
    (does NOT export to Excel — caller decides what to do with results).
    """
    businesses = discover_all(cities, categories, max_results)
    print(f"\n[TOTAL DISCOVERED] {len(businesses)} businesses (before dedup)", flush=True)

    businesses = deduplicate(businesses)
    print(f"[AFTER DEDUP] {len(businesses)} unique businesses\n", flush=True)

    scored = analyze_and_score(businesses, run_performance_check=run_performance)

    qualified = [s for s in scored if lead_scorer.is_qualified_lead(s)]
    print(f"\n[QUALIFIED LEADS] {len(qualified)} out of {len(scored)} businesses", flush=True)

    return qualified
