# Website Lead Generation AI

Finds businesses across multiple Indian cities that either **have no
website** or **have a poorly performing one** — high-intent leads for
web-design/development services.

## How it works (pipeline)

```
DISCOVER  →  DEDUPLICATE  →  ANALYZE  →  SCORE  →  EXPORT (Excel)
```

1. **Discover** — Pull businesses per (city, category) from two sources:
   - **OpenStreetMap / Overpass API** (primary): **completely free, no
     API key, no billing account, no card required.** Community-maintained
     map data — already tells us if a `website` tag is missing.
   - **Justdial scraper** (secondary): fills gaps for hyper-local
     businesses not well-indexed on OSM. Best-effort — Justdial
     has anti-bot protection, so this may return empty results sometimes.
2. **Deduplicate** — merges duplicate businesses found via both sources.
3. **Analyze** — for businesses that DO list a website:
   - `website_checker.py` checks if the site is actually reachable
     (not dead, not a parked/placeholder domain, has SSL).
   - `performance_analyzer.py` calls Google's **PageSpeed Insights API**
     to get an objective 0–100 performance score + mobile-friendliness.
4. **Score** — every business is classified:
   - `NO_WEBSITE` (score ~85-90): no site, or site is dead/parked — hottest lead.
   - `POOR_WEBSITE` (score ~40-80): site is live but slow, not mobile-friendly, no HTTPS, etc — warm lead.
   - `HEALTHY` (score 0): filtered out, not exported.
5. **Export** — qualified leads written to a color-coded, sorted Excel
   file (`leads_output/website_leads.xlsx`) with a summary sheet.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# optional: edit .env and add a PageSpeed API key (see below)
```

Discovery works out of the box with **zero setup** — OpenStreetMap's
Overpass API needs no key, no signup, no billing.

### (Optional) Getting a PageSpeed Insights API key
Only needed for the "website performance score" part of analysis.
Without it, the script still finds `NO_WEBSITE` leads fine; it just
won't score how *poorly* an existing website performs.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → "APIs & Services" → "Library" → enable
   **"PageSpeed Insights API"** (this one does NOT require a linked
   billing account, unlike Places API)
3. "Credentials" → "+ Create Credentials" → **"API key"**
4. Paste it into `.env` as `PAGESPEED_API_KEY=...`

Free tier: 25,000 requests/day — far more than this project needs.

## Usage

### Web UI (recommended)
```bash
python app.py
```
Open **http://127.0.0.1:5000** in your browser. Two ways to search:
- **AI Query tab**: type free text like *"find beauty salons without website in Jaipur"* — parsed by Groq (or simple keyword matching if no Groq key is set) into city/category/limit.
- **Structured Form tab**: pick city + category + max results from dropdowns.

Results show in a color-coded table (red = no website, yellow = poor website) with a **Download Excel** button.

### CLI
```bash
# Full run across all configured cities & categories
python main.py

# Test run: single city, single category, small limit
python main.py --city Jaipur --category "beauty salon" --limit 5

# Skip Justdial (OpenStreetMap only — faster, more reliable)
python main.py --skip-justdial

# Skip PageSpeed checks (faster, but only catches dead/no-website leads, not "poor" ones)
python main.py --skip-performance
```

CLI output: `leads_output/website_leads.xlsx` (same format as the web UI's download)
- **Sheet 1 "Leads"**: full list, sorted by priority score, color-coded
- **Sheet 2 "Summary"**: counts by city, category, and lead type

## Customization
Everything is in `config.py`:
- `TARGET_CITIES` — list of cities to search
- `TARGET_CATEGORIES` — business types to target
- `PERFORMANCE_SCORE_THRESHOLD` — PageSpeed score below which a site counts as "poor"
- `RESPONSE_TIME_THRESHOLD_SECONDS` — load time above which a site counts as "slow"
- `PLACEHOLDER_SIGNALS` — text patterns that identify parked/placeholder domains

## Design decisions (for explaining in interviews)

- **Why OpenStreetMap/Overpass API as the primary discovery source?**
  It's free, requires no billing account, and — like a commercial
  Places API — gives structured tag data (`name`, `website`, `phone`,
  `addr:*`) instead of raw HTML to parse, so a missing `website` tag
  is a clean, direct "no website" signal. The trade-off is coverage:
  OSM data quality depends on community mapping, so results are
  strongest in well-mapped metros and can be sparser in smaller towns.
  (If budget allows later, `src/discovery/google_places.py` is kept
  in the repo as a drop-in alternative — same interface, just needs a
  billed Google Cloud project.)

- **Why is "has a website" not good enough — why also check health?**
  A huge number of small businesses have a website that's dead,
  expired, or a GoDaddy "domain for sale" placeholder. Counting those
  as "has a working site" would silently exclude some of the best
  leads. The `website_checker` module explicitly hunts for these cases.

- **Why PageSpeed Insights over a custom performance heuristic?**
  It's Google's own scoring engine (same one that affects the
  business's actual SEO/ranking), so it's an authoritative, defensible
  number to show a prospective client — "your site scores 32/100 on
  Google's own performance test" is a much stronger pitch than an
  ad-hoc metric.

- **Why score-and-export rather than a live dashboard?**
  Kept the deliverable simple per requirements — a script producing a
  clean Excel file is directly usable by a sales/outreach workflow
  (filter, sort, call down the list) without needing to host anything.

- **Why a Flask web UI on top of the CLI, not instead of it?**
  Both call the exact same `src/pipeline.py` — no duplicated logic.
  The CLI is better for batch/scheduled runs (e.g. a nightly cron
  job covering all cities); the web UI is better for ad-hoc, one-off
  lookups during outreach — "let me quickly check gyms in Pune".

- **Why Groq for the AI query parser instead of a bigger model?**
  The task (map free text to one of ~10 cities and ~14 categories) is
  a small, low-latency classification job, not something that needs a
  frontier model. Groq's free tier + fast inference keeps the search
  box feeling instant. A keyword-matching fallback keeps the feature
  working even with zero API keys configured.

- **Why deduplicate after combining two sources?**
  OpenStreetMap and Justdial can both surface the same business under
  slightly different names — dedup on (normalized name, city) prevents
  double-counting in the summary stats and duplicate outreach.

## Known limitations / next steps
- OSM coverage varies by city — smaller towns will return fewer
  results than metros. Justdial scraping helps fill some gaps but is
  best-effort (may return zero if blocked).
- No ratings/review counts (OSM doesn't track those, unlike Google Places).
- No phone-number validation/formatting normalization yet.

## Deployment (Render.com — free tier)

The web UI is deploy-ready as-is (gunicorn + `Procfile` + `render.yaml` included).

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Website Lead Generation AI"
   # create a repo on github.com, then:
   git remote add origin https://github.com/<your-username>/lead-gen-ai.git
   git push -u origin main
   ```
   (`.gitignore` already excludes `.env`, so your keys stay local — never commit them.)

2. **Create the service on Render**
   - Go to [render.com](https://render.com) → sign up (free, GitHub login works)
   - Dashboard → **"New +"** → **"Web Service"**
   - Connect your GitHub repo
   - Render auto-detects `render.yaml` and pre-fills everything (build
     command, start command, Python version). If it doesn't, set manually:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app --timeout 120`
   - **Instance Type**: Free

3. **Add environment variables** (Render dashboard → your service → "Environment")
   - `PAGESPEED_API_KEY` — optional, for performance scoring
   - `GROQ_API_KEY` — optional, for AI query parsing
   - `FLASK_SECRET_KEY` — any random string (or let `render.yaml` auto-generate one)
   - `FLASK_DEBUG` — set to `false`

4. **Deploy** — Render builds and gives you a live URL like
   `https://website-lead-gen-ai.onrender.com`

### Notes on the free tier
- The free instance **sleeps after 15 minutes of inactivity** and takes
  ~30-50 seconds to wake up on the next request — fine for a portfolio
  demo, not for production traffic.
- Storage is **ephemeral**: generated Excel files in `leads_output/`
  are wiped on every redeploy/restart. That's fine here since the
  download happens immediately after generation — nothing needs to
  persist between sessions.
- For a live demo, keep the **max results small (5-10)** — the
  pipeline processes businesses sequentially with rate-limit delays
  (Overpass, PageSpeed), so large limits can approach the request
  timeout on a free instance.

### Alternatives to Render
- **Railway.app** — similar flow, also has a free trial tier.
- **PythonAnywhere** — good if you want to avoid Docker/gunicorn
  concepts entirely; runs Flask apps directly, free tier available.
- Could add: WHOIS lookup (domain age/expiry), email discovery,
  LangGraph agent wrapper to auto-draft a personalized outreach
  message per lead using the specific `lead_reason`.
