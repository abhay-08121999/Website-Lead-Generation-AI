"""
wayback_checker.py
-------------------
FREE, no API key — uses the Internet Archive's Wayback Machine
"availability" API to find when a website was last archived/changed.

Why this matters: a website can be technically "healthy" (fast,
HTTPS, reachable) while being completely abandoned — no updates in
years, stale contact info, old offers still listed. This is a strong,
easy-to-pitch signal ("your website hasn't changed since 2023") that
PageSpeed alone can't catch.
"""

import requests
from datetime import datetime, timezone
from typing import Dict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config

WAYBACK_API_URL = "https://archive.org/wayback/available"
HEADERS = {"User-Agent": "LeadScope/1.0 (student project)"}


def check_last_updated(url: str) -> Dict:
    """
    Returns:
        {
            "has_snapshot": bool,
            "last_snapshot_date": str or None (YYYY-MM-DD),
            "age_days": int or None,
            "is_stale": bool,   # True if older than config.WAYBACK_STALE_DAYS
            "error": str or None,
        }
    """
    result = {
        "has_snapshot": False,
        "last_snapshot_date": None,
        "age_days": None,
        "is_stale": False,
        "error": None,
    }

    if not url:
        result["error"] = "No URL provided"
        return result

    try:
        resp = requests.get(WAYBACK_API_URL, params={"url": url}, headers=HEADERS, timeout=10)
        data = resp.json()
    except requests.exceptions.Timeout:
        result["error"] = "Wayback Machine request timed out"
        return result
    except requests.RequestException as e:
        result["error"] = f"Wayback request error: {e}"
        return result
    except ValueError:
        result["error"] = "Wayback returned non-JSON response"
        return result

    snapshot = data.get("archived_snapshots", {}).get("closest")
    if not snapshot or not snapshot.get("available"):
        # No archive history — common for very new or very obscure sites.
        # Not itself a red flag, just "no data".
        return result

    timestamp = snapshot.get("timestamp")  # format: YYYYMMDDhhmmss
    if not timestamp:
        return result

    try:
        snapshot_date = datetime.strptime(timestamp[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - snapshot_date).days

        result["has_snapshot"] = True
        result["last_snapshot_date"] = snapshot_date.strftime("%Y-%m-%d")
        result["age_days"] = age_days
        result["is_stale"] = age_days > config.WAYBACK_STALE_DAYS
    except ValueError:
        result["error"] = "Could not parse Wayback timestamp"

    return result
