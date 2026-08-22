"""
url_utils.py
------------
Small shared helpers used across multiple analysis modules
(domain_checker, email_finder, ssl_checker) — avoids repeating the
same URL-parsing logic in three places.
"""

from typing import Optional
from urllib.parse import urlparse


def extract_domain(url: str) -> Optional[str]:
    """Pulls the bare registrable-ish domain out of a URL (strips scheme, www, path, port)."""
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
