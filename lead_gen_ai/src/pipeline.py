"""
pipeline.py
-----------
Core discover -> analyze -> score pipeline, shared by the CLI
(main.py) and the Flask web app (app.py).
"""

import time
from typing import List, Dict

import config
from src.discovery import geoapify_places, here_places, osm_places, duckduckgo_finder
from src.analysis import (
    website_checker, performance_analyzer,
    wayback_checker, domain_checker, crux_checker, safe_browsing_checker,
    ssl_checker, tech_stack_checker, email_finder,
)
from src.scoring import lead_scorer


def discover_all(cities: List[str], categories: List[str], max_results: int) -> List[Dict]:
    all_businesses = []
    for city in cities:
        for category in categories:
            print(f"[DISCOVER] {category} in {city} ...", flush=True)

            combined = []

            # Geoapify and HERE both run as PRIMARY sources — different
            # underlying databases (OSM vs HERE's proprietary map data),
            # so combining them genuinely widens coverage rather than
            # one just backing up the other. Deduplication downstream
            # (deduplicate()) collapses any businesses both find.
            try:
                geo_leads = geoapify_places.discover_leads_for_city_category(city, category, max_results)
                print(f"  -> Geoapify: {len(geo_leads)} businesses", flush=True)
                combined.extend(geo_leads)
            except Exception as e:
                print(f"  [ERROR] Geoapify discovery failed for {city}/{category}: {e}", flush=True)

            try:
                here_leads = here_places.discover_leads_for_city_category(city, category, max_results)
                if here_leads or config.HERE_API_KEY:
                    print(f"  -> HERE: {len(here_leads)} businesses", flush=True)
                combined.extend(here_leads)
            except Exception as e:
                print(f"  [ERROR] HERE discovery failed for {city}/{category}: {e}", flush=True)

            # Fallback to direct Overpass only if BOTH primary sources
            # returned nothing (e.g. no keys configured, or a transient
            # issue with both APIs).
            if not combined:
                try:
                    osm_leads = osm_places.discover_leads_for_city_category(city, category, max_results)
                    print(f"  -> OpenStreetMap (fallback): {len(osm_leads)} businesses", flush=True)
                    combined = osm_leads
                except Exception as e:
                    print(f"  [ERROR] OpenStreetMap fallback failed for {city}/{category}: {e}", flush=True)

            all_businesses.extend(combined)

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

        # Optional, opt-in supplementary check (config.DUCKDUCKGO_ENABLED,
        # default OFF): if no discovery source listed a website, ask
        # DuckDuckGo's official Instant Answer API whether it recognizes
        # this business as a known entity with an official site. Low
        # recall by design — see duckduckgo_finder.py's legal note for
        # why this stays inside DuckDuckGo's documented API rather than
        # scraping their search results pages.
        if not website and config.DUCKDUCKGO_ENABLED:
            ddg_result = duckduckgo_finder.find_website(biz.get("business_name", ""), biz.get("city", ""))
            if ddg_result.get("website"):
                website = ddg_result["website"]
                biz["website"] = website
                biz["website_source"] = ddg_result["source"]
                print(f"  [INFO] DuckDuckGo found a website for {biz.get('business_name')}: {website}", flush=True)
            elif ddg_result.get("error"):
                print(f"  [WARN] DuckDuckGo lookup failed for {biz.get('business_name')}: {ddg_result['error']}", flush=True)

        if not website:
            scored.append(lead_scorer.score_lead(biz))
            continue

        health = website_checker.check_website_health(website)

        # Dead or placeholder sites are already a lead — skip the
        # remaining (slower / quota-limited) checks entirely.
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

        ssl_info = ssl_checker.check_ssl_expiry(website)
        if ssl_info.get("error"):
            print(f"  [WARN] SSL check note for {website}: {ssl_info['error']}", flush=True)
        elif ssl_info.get("is_expiring_soon") or ssl_info.get("is_expired"):
            print(f"  [INFO] {website} SSL expiry: {ssl_info.get('expiry_date')}", flush=True)

        tech_stack = tech_stack_checker.detect_tech_stack(health.get("body_snippet", ""))
        if tech_stack.get("is_template_builder"):
            print(f"  [INFO] {website} built on {tech_stack.get('builder')}", flush=True)

        if config.PAGESPEED_API_KEY:  # CrUX and Safe Browsing use the same Google API key
            crux = crux_checker.check_crux(website, config.PAGESPEED_API_KEY)
            if crux.get("error"):
                print(f"  [WARN] CrUX check failed for {website}: {crux['error']}", flush=True)

            safe_browsing = safe_browsing_checker.check_safe_browsing(website, config.PAGESPEED_API_KEY)
            if safe_browsing.get("error"):
                print(f"  [WARN] Safe Browsing check failed for {website}: {safe_browsing['error']}", flush=True)
            elif safe_browsing.get("is_flagged"):
                print(f"  [WARN] {website} flagged by Safe Browsing!", flush=True)

        scored_biz = lead_scorer.score_lead(biz, health, perf, wayback, domain, crux, safe_browsing, ssl_info, tech_stack)

        # Email lookup is quota-limited (Hunter.io free tier: 25/month) —
        # only spend it on businesses that already qualify as a lead.
        if config.HUNTER_API_KEY and lead_scorer.is_qualified_lead(scored_biz):
            email_result = email_finder.find_email(website, config.HUNTER_API_KEY)
            if email_result.get("email"):
                scored_biz["contact_email"] = email_result["email"]
                print(f"  [INFO] Found contact email for {website}: {email_result['email']}", flush=True)
            elif email_result.get("error"):
                print(f"  [WARN] Email lookup failed for {website}: {email_result['error']}", flush=True)

        scored.append(scored_biz)

    return scored


def run_full_pipeline(cities: List[str], categories: List[str], max_results: int,
                       run_performance: bool = True) -> List[Dict]:
    """
    Full end-to-end pipeline: discover -> dedup -> analyze -> score ->
    filter to qualified leads only.
    """
    businesses = discover_all(cities, categories, max_results)
    print(f"\n[TOTAL DISCOVERED] {len(businesses)} businesses (before dedup)", flush=True)

    businesses = deduplicate(businesses)
    print(f"[AFTER DEDUP] {len(businesses)} unique businesses\n", flush=True)

    scored = analyze_and_score(businesses, run_performance_check=run_performance)

    qualified = [s for s in scored if lead_scorer.is_qualified_lead(s)]
    print(f"\n[QUALIFIED LEADS] {len(qualified)} out of {len(scored)} businesses", flush=True)

    return qualified
