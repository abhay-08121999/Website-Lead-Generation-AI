"""
lead_scorer.py
---------------
Turns raw discovery + analysis data into a single, sales-ready
lead record: category (NO_WEBSITE / POOR_WEBSITE / HEALTHY), a
0-100 priority score, and a human-readable reason.
"""

from typing import Dict, Optional
import config


def score_lead(
    business: Dict,
    website_health: Optional[Dict] = None,
    performance: Optional[Dict] = None,
    wayback: Optional[Dict] = None,
    domain: Optional[Dict] = None,
    crux: Optional[Dict] = None,
    safe_browsing: Optional[Dict] = None,
    ssl_info: Optional[Dict] = None,
    tech_stack: Optional[Dict] = None,
) -> Dict:
    """
    Returns the business dict enriched with:
        lead_category, lead_score, lead_reason, website_status
    """
    enriched = dict(business)
    has_website_field = bool(business.get("website", "").strip())

    # --- Case 1: No website listed at all -> hottest lead ---
    if not has_website_field:
        enriched["lead_category"] = "NO_WEBSITE"
        enriched["lead_score"] = 90
        enriched["lead_reason"] = "No website found in listing — clean opportunity to build one from scratch."
        enriched["website_status"] = "None"
        return enriched

    # --- Case 2: Website exists — evaluate its health ---
    website_health = website_health or {}
    performance = performance or {}
    wayback = wayback or {}
    domain = domain or {}
    crux = crux or {}
    safe_browsing = safe_browsing or {}
    ssl_info = ssl_info or {}
    tech_stack = tech_stack or {}

    if not website_health.get("reachable", False):
        enriched["lead_category"] = "NO_WEBSITE"
        enriched["lead_score"] = 88
        enriched["lead_reason"] = f"Website listed but unreachable ({website_health.get('issue_summary', 'unknown error')}) — effectively no working site."
        enriched["website_status"] = "Dead/Unreachable"
        return enriched

    if website_health.get("is_placeholder", False):
        enriched["lead_category"] = "NO_WEBSITE"
        enriched["lead_score"] = 85
        enriched["lead_reason"] = "Website is a parked/placeholder domain — no real content."
        enriched["website_status"] = "Placeholder"
        return enriched

    # A flagged (malware/phishing) site is a serious, urgent issue on its own
    if safe_browsing.get("is_flagged"):
        enriched["lead_category"] = "POOR_WEBSITE"
        enriched["lead_score"] = 95
        threats = ", ".join(safe_browsing.get("threat_types", [])) or "security threat"
        enriched["lead_reason"] = f"Website flagged by Google Safe Browsing ({threats}) — urgent trust/security issue."
        enriched["website_status"] = "Flagged (unsafe)"
        return enriched

    # Expired/invalid SSL certificate is also urgent — browsers show a
    # scary warning to every visitor.
    if ssl_info.get("is_expired") and ssl_info.get("has_ssl"):
        enriched["lead_category"] = "POOR_WEBSITE"
        enriched["lead_score"] = 90
        enriched["lead_reason"] = f"SSL certificate expired or invalid ({ssl_info.get('error', 'unknown SSL issue')}) — visitors see a security warning."
        enriched["website_status"] = "SSL Expired"
        return enriched

    # Site is reachable and real -> check performance + freshness + trust signals
    perf_score = performance.get("performance_score")
    issues = []

    if perf_score is not None and perf_score < config.PERFORMANCE_SCORE_THRESHOLD:
        issues.append(f"low PageSpeed score ({perf_score}/100)")

    resp_time = website_health.get("response_time")
    if resp_time and resp_time > config.RESPONSE_TIME_THRESHOLD_SECONDS:
        issues.append(f"slow load time ({resp_time}s)")

    if website_health.get("has_ssl") is False:
        issues.append("no HTTPS")

    if performance.get("is_mobile_friendly") is False:
        issues.append("not mobile-friendly")

    status_code = website_health.get("status_code")
    if status_code and status_code >= 400:
        issues.append(f"HTTP error {status_code}")

    if wayback.get("is_stale"):
        years = round(wayback["age_days"] / 365, 1)
        issues.append(f"not updated in {years} years (last change: {wayback.get('last_snapshot_date')})")

    if domain.get("is_expired"):
        issues.append(f"domain already expired ({domain.get('expiry_date')})")
    elif domain.get("is_expiring_soon"):
        issues.append(f"domain expires in {domain.get('days_until_expiry')} days")

    if ssl_info.get("is_expiring_soon"):
        issues.append(f"SSL certificate expires in {ssl_info.get('days_until_expiry')} days")

    if crux.get("is_poor_experience"):
        issues.append("poor real-world user experience (Chrome UX Report)")

    if tech_stack.get("is_template_builder"):
        issues.append(f"built on a free template platform ({tech_stack.get('builder')})")

    if issues:
        enriched["lead_category"] = "POOR_WEBSITE"
        enriched["lead_score"] = min(80, 40 + len(issues) * 8)
        enriched["lead_reason"] = "Underperforming site: " + ", ".join(issues)
        enriched["website_status"] = "Poor"
    else:
        enriched["lead_category"] = "HEALTHY"
        enriched["lead_score"] = 0
        enriched["lead_reason"] = "Website appears healthy — not a lead."
        enriched["website_status"] = "Healthy"

    return enriched


def is_qualified_lead(scored_business: Dict) -> bool:
    """A business is a lead worth exporting if it's NOT categorized as HEALTHY."""
    return scored_business.get("lead_category") != "HEALTHY"
