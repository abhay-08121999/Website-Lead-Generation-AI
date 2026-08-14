"""
safe_browsing_checker.py
-------------------------
Google Safe Browsing API — free, uses the same Google API key
(enable "Safe Browsing API" in Google Cloud Console for the same
project/key).

Why this matters: mostly a trust/safety signal rather than a "poor
website" signal — a flagged site (malware/phishing) is a much more
urgent, serious issue than slow load times, and worth calling out
separately if it ever happens. Rare for small legitimate businesses,
but cheap to check and good practice.
"""

import requests
from typing import Dict

SAFE_BROWSING_API_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


def check_safe_browsing(url: str, api_key: str) -> Dict:
    """
    Returns:
        {
            "is_flagged": bool,
            "threat_types": list[str],
            "error": str or None,
        }
    """
    result = {"is_flagged": False, "threat_types": [], "error": None}

    if not url or not api_key:
        result["error"] = "No URL or API key provided"
        return result

    body = {
        "client": {"clientId": "leadscope", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }

    try:
        resp = requests.post(SAFE_BROWSING_API_URL, params={"key": api_key}, json=body, timeout=10)
        data = resp.json()
    except requests.exceptions.Timeout:
        result["error"] = "Safe Browsing request timed out"
        return result
    except requests.RequestException as e:
        result["error"] = f"Safe Browsing request error: {e}"
        return result
    except ValueError:
        result["error"] = "Safe Browsing returned non-JSON response"
        return result

    if "error" in data:
        result["error"] = data["error"].get("message", "Safe Browsing API error")
        return result

    matches = data.get("matches", [])
    if matches:
        result["is_flagged"] = True
        result["threat_types"] = list({m.get("threatType") for m in matches if m.get("threatType")})

    return result
