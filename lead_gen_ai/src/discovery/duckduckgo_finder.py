"""
duckduckgo_finder.py
---------------------
OPTIONAL, opt-in supplementary check (see config.DUCKDUCKGO_ENABLED,
default OFF). Attempts to find an official website for a business
that the primary discovery sources (Geoapify, HERE, OSM) listed
WITHOUT a website, using DuckDuckGo's own Instant Answer API.

LEGAL NOTE — read before touching or extending this file
----------------------------------------------------------
DuckDuckGo does not publish a general-purpose web-search API. The
only endpoint they document and explicitly permit programmatic use
of is the Instant Answer API (https://duckduckgo.com/api) — a free,
keyless JSON endpoint that returns knowledge-graph "instant answers"
(an infobox summary + an official site link, when DuckDuckGo
recognizes the query as a known entity). It does NOT return ranked
web search results, and it is not a general-purpose crawler
replacement.

This module deliberately does NOT scrape DuckDuckGo's HTML search
results pages (e.g. html.duckduckgo.com/html/, lite.duckduckgo.com),
which is how most "duckduckgo-search"-style scraping libraries work
under the hood. That kind of scraping:
  - is disallowed by DuckDuckGo's robots.txt for automated clients,
  - breaches DuckDuckGo's Terms of Service for bulk/automated
    querying of their results pages, and
  - carries real legal exposure for a tool used commercially (ToS
    breach, IP bans, and — depending on jurisdiction — the kind of
    access-control-circumvention risk that has been litigated under
    laws like the US CFAA / India's IT Act unauthorized-access
    provisions).
So SERP scraping is out of scope here, by design, no matter how much
more "useful" raw search results might look. If a future need
genuinely requires ranked web search results, the correct fix is a
licensed API (e.g. Bing Web Search API, Google Custom Search JSON
API, Brave Search API) with an actual commercial-use ToS — not
working around DuckDuckGo's.

Practical consequence of staying inside DuckDuckGo's legal API
surface: recall is low. The Instant Answer API mostly "knows"
chains/franchises/well-known institutions, not the typical small
independent business this tool targets — so treat any hit as a
bonus, not a primary discovery source. It only ever runs for
businesses that already have no website from Geoapify/HERE/OSM.
"""

import time
import requests
from typing import Dict

import config

DUCKDUCKGO_URL = "https://api.duckduckgo.com/"


def find_website(business_name: str, city: str) -> Dict:
    """
    Best-effort lookup of an official website for a business that
    discovery sources found WITHOUT one. Only ever called when
    config.DUCKDUCKGO_ENABLED is True (default: off) — see pipeline.py.

    Returns:
        {
            "website": str or None,
            "source": "duckduckgo_instant_answer" or None,
            "error": str or None,
        }
    """
    result = {"website": None, "source": None, "error": None}

    business_name = (business_name or "").strip()
    if not business_name:
        result["error"] = "No business name provided"
        return result

    query = f"{business_name} {city}".strip()

    try:
        resp = requests.get(
            DUCKDUCKGO_URL,
            params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            },
            headers={"User-Agent": config.OSM_USER_AGENT},
            timeout=config.DUCKDUCKGO_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        result["error"] = "DuckDuckGo request timed out"
        return result
    except requests.RequestException as e:
        result["error"] = f"DuckDuckGo request error: {e}"
        return result

    if resp.status_code != 200:
        result["error"] = f"DuckDuckGo returned status {resp.status_code}"
        return result

    try:
        data = resp.json()
    except ValueError:
        result["error"] = "DuckDuckGo returned non-JSON response"
        return result

    # AbstractURL is the "official site" link DuckDuckGo's knowledge
    # graph attaches to a recognized entity. Redirect occasionally
    # carries a direct link too (used for !bang-style redirects).
    # Both are empty strings, never missing, when there's no match —
    # so an empty-check here correctly means "no instant answer".
    website = (data.get("AbstractURL") or data.get("Redirect") or "").strip()

    if website:
        result["website"] = website
        result["source"] = "duckduckgo_instant_answer"

    time.sleep(config.DUCKDUCKGO_REQUEST_DELAY)
    return result
