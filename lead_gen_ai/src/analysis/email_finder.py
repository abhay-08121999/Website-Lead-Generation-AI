"""
email_finder.py
----------------
Hunter.io Domain Search API — finds a contact email associated with
a business's domain. Free tier: 25 searches/month, so this is called
sparingly (only for businesses that already qualify as a lead, not
for every business discovered — see pipeline.py).

Free key: https://hunter.io/api-keys
"""

import requests
from typing import Dict

from src.analysis.url_utils import extract_domain

HUNTER_URL = "https://api.hunter.io/v2/domain-search"


def find_email(url: str, api_key: str) -> Dict:
    """
    Returns:
        {
            "email": str or None,
            "confidence": int or None,  # 0-100, Hunter's confidence score
            "error": str or None,
        }
    """
    result = {"email": None, "confidence": None, "error": None}

    if not url or not api_key:
        result["error"] = "No URL or API key provided"
        return result

    domain = extract_domain(url)
    if not domain:
        result["error"] = "Could not parse domain from URL"
        return result

    try:
        resp = requests.get(
            HUNTER_URL,
            params={"domain": domain, "api_key": api_key, "limit": 1},
            timeout=10,
        )
        data = resp.json()
    except requests.exceptions.Timeout:
        result["error"] = "Hunter.io request timed out"
        return result
    except requests.RequestException as e:
        result["error"] = f"Hunter.io request error: {e}"
        return result
    except ValueError:
        result["error"] = "Hunter.io returned non-JSON response"
        return result

    if "errors" in data:
        err = data["errors"][0] if data["errors"] else {}
        result["error"] = err.get("details", err.get("id", "Hunter.io API error"))
        return result

    emails = data.get("data", {}).get("emails", [])
    if emails:
        result["email"] = emails[0].get("value")
        result["confidence"] = emails[0].get("confidence")

    return result
