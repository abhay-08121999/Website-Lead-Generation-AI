"""
domain_checker.py
------------------
FREE, no API key — uses the `python-whois` library to query domain
registration data directly (WHOIS protocol, not a REST API).
"""

from datetime import datetime, timezone
from typing import Dict

import config
from src.analysis.url_utils import extract_domain


def check_domain_expiry(url: str) -> Dict:
    result = {
        "domain": None,
        "expiry_date": None,
        "days_until_expiry": None,
        "is_expiring_soon": False,
        "is_expired": False,
        "error": None,
    }

    domain = extract_domain(url)
    result["domain"] = domain
    if not domain:
        result["error"] = "Could not parse domain from URL"
        return result

    try:
        import whois
    except ImportError:
        result["error"] = "python-whois not installed"
        return result

    try:
        w = whois.whois(domain)
    except Exception as e:
        result["error"] = f"WHOIS lookup failed: {e}"
        return result

    expiry = w.expiration_date
    if isinstance(expiry, list):
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
