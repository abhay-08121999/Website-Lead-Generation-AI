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
# Overpass, Nominatim, PageSpeed, Geoapify, and Groq calls alike.
def _force_ipv4():
    return socket.AF_INET

_urllib3_cn.allowed_gai_family = _force_ipv4

# ---------------------------------------------------------------------
# API KEYS
# ---------------------------------------------------------------------
# Google PageSpeed Insights API — used only for website performance
# scoring. Get a free key at https://console.cloud.google.com/ ->
# enable "PageSpeed Insights API" -> Credentials -> Create API Key.
# This API does NOT require a linked billing account (unlike Places API).
# The same key is reused for Chrome UX Report + Safe Browsing (enable
# those APIs too in the same GCP project).
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY", "")

# Groq API — used ONLY by the web UI's "AI query" free-text search box
# (parses natural language into city/category/limit). Optional —
# without it, free-text search falls back to simple keyword matching.
# Free key: https://console.groq.com/keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Geoapify Places API — PRIMARY discovery source. Free tier: 3,000
# requests/day, no credit card required. Same underlying OpenStreetMap
# data as before, but served from Geoapify's own dedicated
# infrastructure rather than the public Overpass mirrors — which
# frequently reject connections from cloud-hosting IP ranges
# (including Render's), causing silent 0-result discovery.
# Get a free key: https://myprojects.geoapify.com/ -> Create project -> API Keys
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "")

# Hunter.io Email Finder — OPTIONAL. Finds a contact email for a
# business's domain. Free tier: 25 searches/month — quite limited,
# so this is only called for businesses that already qualify as leads
# (not for every business discovered). Free key: https://hunter.io/api-keys
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

# ---------------------------------------------------------------------
# TARGET CITIES (multi-city scope)
# ---------------------------------------------------------------------
TARGET_CITIES = [
    # Top-tier — hardcoded bbox in CITY_BBOXES below (instant, no geocoding call)
    "Jaipur", "Delhi", "Mumbai", "Bangalore", "Pune", "Ahmedabad", "Lucknow",
    "Chandigarh", "Indore", "Surat", "Kochi", "Hyderabad", "Chennai", "Kolkata",
    "Bhopal", "Nagpur", "Coimbatore", "Visakhapatnam", "Vadodara", "Nashik",
    "Rajkot", "Varanasi", "Amritsar", "Ludhiana", "Kanpur", "Agra", "Meerut",
    "Ranchi", "Raipur", "Dehradun", "Jodhpur", "Udaipur", "Mysore", "Madurai",
    "Vijayawada", "Gurugram", "Noida", "Faridabad", "Ghaziabad", "Jamshedpur",
    "Siliguri", "Shimla", "Guntur", "Aurangabad", "Jabalpur", "Gwalior",
    "Prayagraj", "Salem", "Tiruchirappalli", "Kolhapur", "Mangalore", "Hubli",
    "Panaji", "Puducherry", "Kota", "Jalandhar",
    # Extended list — resolved dynamically via Geoapify geocoding at
    # search time (see src/discovery/geocoding.py), cached per run.
    "Bareilly", "Moradabad", "Aligarh", "Saharanpur", "Gorakhpur", "Bhagalpur",
    "Muzaffarpur", "Gaya", "Darbhanga", "Cuttack", "Rourkela", "Bhilai",
    "Bilaspur", "Durg", "Korba", "Ajmer", "Bikaner", "Alwar", "Bhilwara",
    "Sikar", "Bhavnagar", "Jamnagar", "Junagadh", "Gandhinagar", "Anand",
    "Nadiad", "Solapur", "Amravati", "Akola", "Latur", "Sangli", "Satara",
    "Thane", "Navi Mumbai", "Vasai-Virar", "Kalyan", "Bhiwandi", "Malegaon",
    "Ichalkaranji", "Nanded", "Parbhani", "Belgaum", "Davanagere", "Bellary",
    "Gulbarga", "Shimoga", "Tumkur", "Bidar", "Hospet", "Erode", "Vellore",
    "Thoothukudi", "Dindigul", "Thanjavur", "Tirunelveli", "Cuddalore",
    "Kanchipuram", "Karur", "Rajahmundry", "Nellore", "Kurnool", "Kadapa",
    "Anantapur", "Tirupati", "Ongole", "Warangal", "Nizamabad", "Karimnagar",
    "Khammam", "Kollam", "Kottayam", "Kannur", "Thrissur", "Alappuzha",
    "Palakkad", "Malappuram", "Bathinda", "Patiala", "Mohali", "Hoshiarpur",
    "Pathankot", "Karnal", "Panipat", "Hisar", "Rohtak", "Sonipat", "Ambala",
    "Yamunanagar", "Bhiwani", "Sirsa", "Muzaffarnagar", "Rampur", "Firozabad",
    "Jhansi", "Mathura", "Etawah", "Bahraich", "Basti", "Sultanpur", "Ayodhya",
    "Hardoi", "Unnao", "Bulandshahr", "Shahjahanpur", "Mirzapur", "Amroha",
    "Bijnor", "Fatehpur", "Deoria", "Azamgarh", "Mau", "Jaunpur", "Ghazipur",
    "Sitapur", "Barabanki", "Katni", "Sagar", "Rewa", "Satna", "Chhindwara",
    "Ratlam", "Ujjain", "Dewas", "Vidisha", "Khandwa", "Burhanpur", "Balasore",
    "Berhampur", "Sambalpur", "Puri", "Bardhaman", "Asansol", "Durgapur",
    "Malda", "Kharagpur", "Haldia", "Krishnanagar", "Baharampur", "Dhanbad",
    "Bokaro", "Deoghar", "Hazaribagh", "Giridih", "Purnia", "Arrah",
    "Begusarai", "Katihar", "Chapra", "Motihari", "Bihar Sharif", "Godhra",
    "Bharuch", "Navsari", "Valsad", "Porbandar", "Morbi", "Patan", "Mehsana",
    "Pali", "Barmer", "Bharatpur", "Chittorgarh", "Sawai Madhopur", "Nagaur",
    "Sirohi",
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
# OPENSTREETMAP CATEGORY -> TAG MAPPING (fallback discovery source)
# ---------------------------------------------------------------------
OSM_CATEGORY_TAGS = {
    "restaurant": [("amenity", "restaurant")],
    "beauty salon": [("shop", "beauty"), ("shop", "hairdresser")],
    "gym": [("leisure", "fitness_centre")],
    "dental clinic": [("amenity", "dentist")],
    "boutique clothing store": [("shop", "boutique"), ("shop", "clothes")],
    "real estate agent": [("office", "estate_agent")],
    "interior designer": [("craft", "interior_decorator"), ("office", "interior_designer"), ("office", "architect")],
    "photographer": [("shop", "photo"), ("craft", "photographer")],
    "event planner": [("office", "event_management")],
    "electrician": [("craft", "electrician")],
    "coaching institute": [("amenity", "language_school"), ("office", "educational_institution")],
    "car repair shop": [("shop", "car_repair")],
    "bakery": [("shop", "bakery")],
    "yoga studio": [("leisure", "fitness_centre"), ("sport", "yoga")],
}

# ---------------------------------------------------------------------
# GEOAPIFY CATEGORY MAPPING (primary discovery source)
# ---------------------------------------------------------------------
# https://apidocs.geoapify.com/docs/places/#categories
GEOAPIFY_CATEGORY_MAP = {
    "restaurant": "catering.restaurant",
    "beauty salon": "service.beauty.hairdresser",
    "gym": "sport.fitness.gym",
    "dental clinic": "healthcare.dentist",
    "boutique clothing store": "commercial.clothing.clothes",
    "real estate agent": "office.estate_agent",
    "interior designer": "commercial.furniture_and_interior,office.architect",  # no exact match — widened
    "photographer": "service.photographer",
    "event planner": "commercial.wedding",  # closest available match
    "electrician": "service.electrician",
    "coaching institute": "education.language_school",
    "car repair shop": "service.vehicle.repair.car",
    "bakery": "commercial.food_and_drink.bakery",
    "yoga studio": "sport.fitness.fitness_centre",  # closest available match
}

# ---------------------------------------------------------------------
# WEBSITE PERFORMANCE THRESHOLDS
# ---------------------------------------------------------------------
PERFORMANCE_SCORE_THRESHOLD = 50
RESPONSE_TIME_THRESHOLD_SECONDS = 4.0

# Wayback Machine: if a site hasn't changed in this many days, flag it
# as "digitally abandoned".
WAYBACK_STALE_DAYS = 730  # ~2 years

# WHOIS / SSL: flag domains or certs expiring within this many days.
DOMAIN_EXPIRY_WARNING_DAYS = 60

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
# OVERPASS (fallback discovery — used only if Geoapify returns nothing)
# ---------------------------------------------------------------------
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
    "Kochi":         (9.85, 76.20, 10.10, 76.40),
    "Hyderabad":     (17.25, 78.30, 17.55, 78.65),
    "Chennai":       (12.90, 80.15, 13.20, 80.30),
    "Kolkata":       (22.45, 88.25, 22.65, 88.45),
    "Bhopal":        (23.15, 77.30, 23.30, 77.50),
    "Nagpur":        (21.05, 78.95, 21.20, 79.15),
    "Coimbatore":    (10.95, 76.90, 11.10, 77.05),
    "Visakhapatnam": (17.65, 83.20, 17.80, 83.35),
    "Vadodara":         (22.25, 73.10, 22.40, 73.25),
    "Nashik":           (19.90, 73.70, 20.05, 73.85),
    "Rajkot":           (22.25, 70.75, 22.35, 70.85),
    "Varanasi":         (25.25, 82.95, 25.35, 83.05),
    "Amritsar":         (31.55, 74.80, 31.70, 74.95),
    "Ludhiana":         (30.85, 75.80, 30.95, 75.90),
    "Kanpur":           (26.40, 80.25, 26.55, 80.40),
    "Agra":             (27.13, 77.95, 27.25, 78.10),
    "Meerut":           (28.95, 77.65, 29.05, 77.75),
    "Ranchi":           (23.30, 85.28, 23.40, 85.38),
    "Raipur":           (21.20, 81.55, 21.30, 81.70),
    "Dehradun":         (30.28, 77.98, 30.38, 78.10),
    "Jodhpur":          (26.24, 73.00, 26.34, 73.10),
    "Udaipur":          (24.55, 73.65, 24.65, 73.75),
    "Mysore":           (12.28, 76.60, 12.35, 76.70),
    "Madurai":          (9.88, 78.08, 9.98, 78.18),
    "Vijayawada":       (16.48, 80.60, 16.55, 80.68),
    "Gurugram":         (28.40, 76.98, 28.50, 77.10),
    "Noida":            (28.53, 77.30, 28.63, 77.40),
    "Faridabad":        (28.35, 77.25, 28.45, 77.35),
    "Ghaziabad":        (28.63, 77.40, 28.73, 77.50),
    "Jamshedpur":       (22.75, 86.15, 22.85, 86.25),
    "Siliguri":         (26.68, 88.38, 26.75, 88.45),
    "Shimla":           (31.08, 77.14, 31.12, 77.20),
    "Guntur":           (16.28, 80.42, 16.35, 80.50),
    "Aurangabad":       (19.85, 75.30, 19.92, 75.38),
    "Jabalpur":         (23.14, 79.92, 23.22, 80.00),
    "Gwalior":          (26.18, 78.15, 26.25, 78.22),
    "Prayagraj":        (25.40, 81.80, 25.50, 81.90),
    "Salem":            (11.62, 78.12, 11.70, 78.20),
    "Tiruchirappalli":  (10.78, 78.65, 10.85, 78.72),
    "Kolhapur":         (16.68, 74.22, 16.75, 74.28),
    "Mangalore":        (12.85, 74.83, 12.92, 74.90),
    "Hubli":            (15.33, 75.10, 15.40, 75.18),
    "Panaji":           (15.47, 73.80, 15.52, 73.86),
    "Puducherry":       (11.90, 79.78, 11.97, 79.85),
    "Kota":             (25.13, 75.80, 25.22, 75.88),
    "Jalandhar":        (31.30, 75.55, 31.35, 75.62),
}

# Used only as a FALLBACK (if a city isn't in CITY_BBOXES above) to
# resolve it to a bounding box.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REQUEST_DELAY = 1.0  # Nominatim policy: max 1 request/sec

# Overpass/OSM usage policy asks for an identifying User-Agent.
OSM_USER_AGENT = "LeadGenAI/1.0 (student project; contact: your-email@example.com)"

# ---------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------
OUTPUT_DIR = "leads_output"
OUTPUT_FILENAME = "website_leads.xlsx"

# Politeness delay between outbound requests (seconds)
REQUEST_DELAY = 1.5
