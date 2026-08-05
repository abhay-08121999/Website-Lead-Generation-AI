"""
performance_analyzer.py
------------------------
Uses Google's PageSpeed Insights API (free) to get an objective
0-100 performance score for a website, plus mobile-friendliness
signals. This is what separates "technically online" from
"actually performing well".

API docs: https://developers.google.com/speed/docs/insights/v5/get-started
Free tier: 25,000 requests/day per project — more than enough here.
"""

import requests
from typing import Dict

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def analyze_performance(url: str, api_key: str, strategy: str = "mobile") -> Dict:
    """
    Returns:
        {
            "performance_score": int or None (0-100),
            "is_mobile_friendly": bool or None,
            "first_contentful_paint": str or None,
            "error": str or None,
        }
    """
    result = {
        "performance_score": None,
        "is_mobile_friendly": None,
        "first_contentful_paint": None,
        "error": None,
    }

    if not url:
        result["error"] = "No URL provided"
        return result

    params = {
        "url": url,
        "key": api_key,
        "strategy": strategy,
        "category": "PERFORMANCE",
    }

    try:
        resp = requests.get(PAGESPEED_URL, params=params, timeout=30)
        data = resp.json()

        if "error" in data:
            result["error"] = data["error"].get("message", "PageSpeed API error")
            return result

        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        perf = categories.get("performance", {})

        if perf.get("score") is not None:
            result["performance_score"] = round(perf["score"] * 100)

        audits = lighthouse.get("audits", {})
        fcp = audits.get("first-contentful-paint", {})
        result["first_contentful_paint"] = fcp.get("displayValue")

        viewport_audit = audits.get("viewport", {})
        result["is_mobile_friendly"] = viewport_audit.get("score") == 1

    except requests.exceptions.Timeout:
        result["error"] = "PageSpeed analysis timed out"
    except requests.RequestException as e:
        result["error"] = f"Request error: {e}"

    return result
