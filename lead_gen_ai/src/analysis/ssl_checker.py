"""
tech_stack_checker.py
----------------------
FREE, no external API — looks for known fingerprints (CSS/JS asset
paths, meta generator tags, branding strings) in HTML that's already
been fetched by website_checker.py, to identify which platform a
site was built on. No second HTTP request needed.

Why this matters: a site built on a free-tier template builder
(Wix, Weebly, GoDaddy Website Builder, Blogspot) is a strong signal
of a low-investment, DIY website — even if it's technically fast and
reachable, it's a very different (and usually easier) pitch than a
site that's slow because of genuine technical debt.
"""

from typing import Dict

# Each entry: (display name, list of substrings that identify it in the HTML)
BUILDER_SIGNATURES = [
    ("Wix", ["static.wixstatic.com", "wix.com", "_wixcssrichtext", "wixsite.com"]),
    ("WordPress", ["wp-content", "wp-includes", "/wp-json/"]),
    ("GoDaddy Website Builder", ["godaddy.com/websites", "gdwebsitebuilder", "wsimg.com"]),
    ("Squarespace", ["squarespace.com", "static1.squarespace.com"]),
    ("Weebly", ["weebly.com", "cdn2.editmysite.com"]),
    ("Shopify", ["cdn.shopify.com", "myshopify.com"]),
    ("Blogspot/Blogger", ["blogspot.com", "blogger.com"]),
    ("Wordpress.com (free)", ["wordpress.com/wp-json", ".wordpress.com"]),
    ("Zyro", ["zyro.com"]),
    ("IndiaMART site builder", ["indiamart.com/proddetail", "static.indiamart.com"]),
]

# Builders whose free tiers are especially common for very low-investment
# sites — used to flag with slightly stronger language.
FREE_TIER_COMMON = {"Wix", "Weebly", "Blogspot/Blogger", "Wordpress.com (free)", "GoDaddy Website Builder"}


def detect_tech_stack(body_snippet: str) -> Dict:
    """
    body_snippet: lowercased HTML text (already fetched — see
    website_checker.check_website_health's 'body_snippet' field).

    Returns:
        {
            "builder": str or None,
            "is_template_builder": bool,  # True if built on any known template platform
        }
    """
    result = {"builder": None, "is_template_builder": False}

    if not body_snippet:
        return result

    for builder_name, signatures in BUILDER_SIGNATURES:
        if any(sig in body_snippet for sig in signatures):
            result["builder"] = builder_name
            result["is_template_builder"] = True
            break

    return result
