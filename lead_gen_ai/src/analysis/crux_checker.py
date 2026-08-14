"""
crux_checker.py
----------------
Chrome UX Report (CrUX) API — free, uses the same Google API key as
PageSpeed Insights (enable "Chrome UX Report API" in Google Cloud
Console for the same project/key).

Why this matters: PageSpeed Insights gives *lab* data (a simulated
test run). CrUX gives *field* data — real measurements from actual
Chrome users who visited the site. When both agree, that's a much
stronger case. Not every site has CrUX data though — Google only
publishes it for sites with enough real-world traffic, so a missing
record is common and NOT itself a red flag (just means "no data",
handled as such rather than as an error).
"""

import requests
from typing import Dict

CRUX_API_URL = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"

# CrUX buckets each metric into these categories
POOR = "POOR"


def check_crux(url: str, api_key: str) -> Dict:
    """
    Returns:
        {
            "has_data": bool,
            "lcp_rating": str or None,   # largest contentful paint: GOOD / NEEDS_IMPROVEMENT / POOR
            "cls_rating": str or None,   # cumulative layout shift
            "inp_rating": str or None,   # interaction to next paint
            "is_poor_experience": bool,  # True if any metric rates POOR
            "error": str or None,
        }
    """
    result = {
        "has_data": False,
        "lcp_rating": None,
        "cls_rating": None,
        "inp_rating": None,
        "is_poor_experience": False,
        "error": None,
    }

    if not url or not api_key:
        result["error"] = "No URL or API key provided"
        return result

    try:
        resp = requests.post(
            CRUX_API_URL,
            params={"key": api_key},
            json={"url": url, "formFactor": "PHONE"},
            timeout=10,
        )
        data = resp.json()
    except requests.exceptions.Timeout:
        result["error"] = "CrUX request timed out"
        return result
    except requests.RequestException as e:
        result["error"] = f"CrUX request error: {e}"
        return result
    except ValueError:
        result["error"] = "CrUX returned non-JSON response"
        return result

    # CrUX returns a 404-style error body when there's no data for this URL —
    # this is common and expected for smaller sites, not a real error.
    if "error" in data:
        code = data["error"].get("code")
        if code == 404:
            return result  # has_data stays False, no error — just "no data available"
        result["error"] = data["error"].get("message", "CrUX API error")
        return result

    metrics = data.get("record", {}).get("metrics", {})
    if not metrics:
        return result

    def _rating(metric_key):
        histogram = metrics.get(metric_key, {}).get("histogram", [])
        if not histogram:
            return None
        # The histogram has 3 buckets (good/needs-improvement/poor) as densities;
        # take the bucket with the highest density as the overall rating.
        labels = ["GOOD", "NEEDS_IMPROVEMENT", "POOR"]
        densities = [b.get("density", 0) for b in histogram]
        if not densities:
            return None
        return labels[densities.index(max(densities))]

    result["has_data"] = True
    result["lcp_rating"] = _rating("largest_contentful_paint")
    result["cls_rating"] = _rating("cumulative_layout_shift")
    result["inp_rating"] = _rating("interaction_to_next_paint")
    result["is_poor_experience"] = POOR in (result["lcp_rating"], result["cls_rating"], result["inp_rating"])

    return result
