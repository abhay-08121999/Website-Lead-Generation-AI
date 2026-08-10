"""
config.py
---------
Central configuration for the Website Lead Generation AI.

Sab settings yahan hai — API keys, target cities, business categories,
aur scoring thresholds. Isse edit karke hi tum pura pipeline customize
kar sakte ho, code kahin aur touch karne ki zaroorat nahi.
"""

import os
import socket
import urllib3.util.connection as _urllib3_cn
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------
# FORCE IPv4 FOR ALL OUTBOUND REQUESTS
# ---------------------------------------------------------------------
# Some hosting platforms (Render's free tier included) don't route
# IPv6 egress traffic, but hosts like overpass-api.de resolve to an
# IPv6 address first — causing "Network is unreachable" errors even
# though the server itself is fine. Forcing IPv4 resolution here
# (applies globally, since this module is imported before any HTTP
# calls happen anywhere in the app) fixes that class of failure for
# Overpass, Nominatim, PageSpeed, and Groq calls alike.
def _force_ipv4():
    return socket.AF_INET

_urllib3_cn.allowed_gai_family = _force_ipv4

# ---------------------------------------------------------------------
# API KEYS
# ---------------------------------------------------------------------
# Discovery (OpenStreetMap / Overpass API) needs NO key — it's fully
# free and open, no billing account required. See src/discovery/osm_places.py.

# Google PageSpeed Insights API — used only for website performance
# scoring. Get a free key at https://console.cloud.google.com/ ->
# enable "PageSpeed Insights API" -> Credentials -> Create API Key.
# This API does NOT require a linked billing account (unlike Places API).
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY", "")

# Groq API — used ONLY by the web UI's "AI query" free-text search box
# (parses natural language into city/category/limit). Optional —
# without it, free-text search falls back to simple keyword matching.
# Free key: https://console.groq.com/keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ---------------------------------------------------------------------
# TARGET CITIES (multi-city scope)
# ---------------------------------------------------------------------
TARGET_CITIES = [
    "Jaipur",
    "Delhi",
    "Mumbai",
    "Bangalore",
    "Pune",
    "Ahmedabad",
    "Lucknow",
    "Chandigarh",
    "Indore",
    "Surat",
]

# ---------------------------------------------------------------------
# BUSINESS CATEGORIES
# Ye woh SMB categories hain jo aam taur par ya to website rakhte hi
# nahi, ya bahut purani/broken website rakhte hain — high-intent leads.
# ---------------------------------------------------------------------
TARGET_CATEGORIES = [
    "restaurant",
    "beauty salon",
    "gym",
    "dental clinic",
    "boutique clothing store",
    "real estate agent",
    "interior designer",
    "photographer",
    "event planner",
    "electrician",
    "coaching institute",
    "car repair shop",
    "bakery",
    "yoga studio",
]

# How many results to pull per (city, category) combo
RESULTS_PER_QUERY = 20

# ---------------------------------------------------------------------
# OPENSTREETMAP CATEGORY -> TAG MAPPING (free discovery source, no
# billing/card required). OSM tagging is community-driven and
# inconsistent, so several tag pairs are tried per category and
# results are merged.
# ---------------------------------------------------------------------
OSM_CATEGORY_TAGS = {
    "restaurant": [("amenity", "restaurant")],
    "beauty salon": [("shop", "beauty"), ("shop", "hairdresser")],
    "gym": [("leisure", "fitness_centre")],
    "dental clinic": [("amenity", "dentist")],
    "boutique clothing store": [("shop", "boutique"), ("shop", "clothes")],
    "real estate agent": [("office", "estate_agent")],
    "interior designer": [("craft", "interior_decorator"), ("office", "interior_designer")],
    "photographer": [("shop", "photo"), ("craft", "photographer")],
    "event planner": [("office", "event_management")],
    "electrician": [("craft", "electrician")],
    "coaching institute": [("amenity", "language_school"), ("office", "educational_institution")],
    "car repair shop": [("shop", "car_repair")],
    "bakery": [("shop", "bakery")],
    "yoga studio": [("leisure", "fitness_centre"), ("sport", "yoga")],
}

# Overpass API is a shared free public resource — be gentle to avoid
# getting temporarily rate-limited. Multiple public mirrors listed as
# fallback since the main instance can be slow/overloaded.
OVERPASS_REQUEST_DELAY = 6.0
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]
OVERPASS_TIMEOUT_SECONDS = 25

# ---------------------------------------------------------------------
# HARDCODED CITY BOUNDING BOXES (south, west, north, east)
# ---------------------------------------------------------------------
# Public Nominatim geocoding is unreliable (rate-limited or outright
# blocked with 403s depending on network/ISP). Since our target city
# list is fixed, we hardcode approximate bounding boxes for them —
# no geocoding API call needed at all for these. Nominatim is only
# used as a fallback if someone passes --city with a city not in this
# dict.
CITY_BBOXES = {
    "Jaipur":     (26.75, 75.65, 27.05, 75.95),
    "Delhi":      (28.40, 76.83, 28.90, 77.35),
    "Mumbai":     (18.89, 72.77, 19.28, 72.98),
    "Bangalore":  (12.83, 77.45, 13.14, 77.75),
    "Pune":       (18.43, 73.75, 18.65, 73.95),
    "Ahmedabad":  (22.95, 72.45, 23.15, 72.70),
    "Lucknow":    (26.75, 80.85, 26.95, 81.05),
    "Chandigarh": (30.65, 76.70, 30.80, 76.85),
    "Indore":     (22.65, 75.75, 22.80, 75.95),
    "Surat":      (21.10, 72.75, 21.30, 72.95),
}

# Used only as a FALLBACK (if a city isn't in CITY_BBOXES above) to
# resolve it to a bounding box.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REQUEST_DELAY = 1.0  # Nominatim policy: max 1 request/sec

# Overpass/OSM usage policy asks for an identifying User-Agent.
# Edit this to include your own contact info before heavy use.
OSM_USER_AGENT = "LeadGenAI/1.0 (student project; contact: your-email@example.com)"

# ---------------------------------------------------------------------
# WEBSITE PERFORMANCE THRESHOLDS
# ---------------------------------------------------------------------
# PageSpeed score is 0-100. Below this => "poorly performing" lead.
PERFORMANCE_SCORE_THRESHOLD = 50

# If a site takes longer than this to respond, treat it as "slow/broken"
RESPONSE_TIME_THRESHOLD_SECONDS = 4.0

# Known "placeholder" / parked-domain signals we treat as "no real website"
PLACEHOLDER_SIGNALS = [
    "domain is for sale",
    "this domain may be for sale",
    "buy this domain",
    "godaddy.com/domains",
    "coming soon",
    "under construction",
    "index of /",
    "default web page",
    "apache2 debian default page",
    "welcome to nginx",
]

# ---------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------
OUTPUT_DIR = "leads_output"
OUTPUT_FILENAME = "website_leads.xlsx"

# Politeness delay between outbound requests (seconds) to avoid
# hammering sites / getting IP-blocked
REQUEST_DELAY = 1.5
