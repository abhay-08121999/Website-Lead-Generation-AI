"""
website_checker.py
-------------------
For businesses that DO have a website listed, this module checks
whether that website is actually "real and working" or effectively
as-good-as-no-website (dead domain, parked page, broken SSL, etc).

This is the key logic that turns "has a website field" into an
honest "has a WORKING website" signal.
"""

import time
import requests
from typing import Dict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LeadGenBot/1.0)"}


def check_website_health(url: str) -> Dict:
    """
    Fetch the website and classify its basic health.

    Returns a dict:
        {
            "reachable": bool,
            "status_code": int or None,
            "response_time": float or None,
            "is_placeholder": bool,
            "has_ssl": bool,
            "issue_summary": str,
        }
    """
    result = {
        "reachable": False,
        "status_code": None,
        "response_time": None,
        "is_placeholder": False,
        "has_ssl": url.strip().lower().startswith("https://"),
        "issue_summary": "",
    }

    if not url:
        result["issue_summary"] = "No website"
        return result

    try:
        start = time.time()
        resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        elapsed = time.time() - start

        result["reachable"] = True
        result["status_code"] = resp.status_code
        result["response_time"] = round(elapsed, 2)

        body_lower = resp.text.lower()[:5000]  # only need to scan the head/top of page
        for signal in config.PLACEHOLDER_SIGNALS:
            if signal in body_lower:
                result["is_placeholder"] = True
                break

        issues = []
        if resp.status_code >= 400:
            issues.append(f"HTTP {resp.status_code} error")
        if elapsed > config.RESPONSE_TIME_THRESHOLD_SECONDS:
            issues.append(f"slow response ({elapsed:.1f}s)")
        if result["is_placeholder"]:
            issues.append("placeholder/parked page")
        if not result["has_ssl"]:
            issues.append("no HTTPS/SSL")
        if len(resp.text.strip()) < 200:
            issues.append("near-empty page")

        result["issue_summary"] = "; ".join(issues) if issues else "OK"

    except requests.exceptions.SSLError:
        result["issue_summary"] = "SSL certificate error"
    except requests.exceptions.Timeout:
        result["issue_summary"] = "Timed out (site very slow or down)"
    except requests.exceptions.ConnectionError:
        result["issue_summary"] = "Connection failed (site likely down)"
    except requests.RequestException as e:
        result["issue_summary"] = f"Request error: {e}"

    return result
