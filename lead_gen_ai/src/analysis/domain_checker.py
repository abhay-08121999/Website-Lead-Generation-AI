"""
domain_checker.py
------------------
FREE, no API key — uses the `python-whois` library to query domain
registration data directly (WHOIS protocol, not a REST API).

Why this matters: a domain expiring soon (or already expired but
still resolving via cache/CDN) means the business could go completely
offline any day without realizing it — a very concrete, urgent pitch
point for outreach.

Note: WHOIS lookups go out over raw sockets (port 43), not HTTP —
some restrictive network environments block this. Fails gracefully
if so (returns empty result, doesn't crash the pipeline).
"""

from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.parse import urlparse

import config


def _extract_domain(url: str) -> Optional[str]:
    """Pulls the bare registrable-ish domain out of a URL (strips scheme, www, path)."""
    try:
        netloc = urlparse(url if "://" in url else f"http://{url}").netloc
        if not netloc:
            return None
        netloc = netloc.split(":")[0]  # drop port if present
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return None


def check_domain_expiry(url: str) -> Dict:
    """
    Returns:
        {
            "domain": str or None,
            "expiry_date": str or None (YYYY-MM-DD),
            "days_until_expiry": int or None,
            "is_expiring_soon": bool,  # within config.DOMAIN_EXPIRY_WARNING_DAYS
            "is_expired": bool,
            "error": str or None,
        }
    """
    result = {
        "domain": None,
        "expiry_date": None,
        "days_until_expiry": None,
        "is_expiring_soon": False,
        "is_expired": False,
        "error": None,
    }

    domain = _extract_domain(url)
    result["domain"] = domain
    if not domain:
        result["error"] = "Could not parse domain from URL"
        return result

    try:
        import whois  # imported lazily so the whole app doesn't fail if the package is missing
    except ImportError:
        result["error"] = "python-whois not installed"
        return result

    try:
        w = whois.whois(domain)
    except Exception as e:
        result["error"] = f"WHOIS lookup failed: {e}"
        return result

    expiry = w.expiration_date
    if isinstance(expiry, list):  # some registries return multiple dates
        expiry = expiry[0] if expiry else None

    if not expiry:
        result["error"] = "No expiry date in WHOIS response"
        return result

    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    days_left = (expiry - datetime.now(timezone.utc)).days

    result["expiry_date"] = expiry.strftime("%Y-%m-%d")
    result["days_until_expiry"] = days_left
    result["is_expired"] = days_left < 0
    result["is_expiring_soon"] = 0 <= days_left <= config.DOMAIN_EXPIRY_WARNING_DAYS

    return result
