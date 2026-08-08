"""
app.py
------
Flask web frontend for the Website Lead Generation AI.

Two ways to query, both hitting the same pipeline:
  1. AI free-text box ("find beauty salons without website in Jaipur")
     -> parsed via Groq (or keyword fallback) -> structured params
  2. Structured dropdown form (city + category + limit)

Run:
    python app.py
Then open http://127.0.0.1:5000 in a browser.
"""

import os
import re
import time

from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for

import config
from src.pipeline import run_full_pipeline
from src.output import export
from src.nlp.query_parser import parse_query_with_ai

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-this-in-production")

os.makedirs(config.OUTPUT_DIR, exist_ok=True)  # ensure this exists even when run via gunicorn (not just __main__)

CATEGORY_LIST = list(config.OSM_CATEGORY_TAGS.keys())


def _safe_filename(text: str) -> str:
    """Turns arbitrary text into a filesystem-safe filename fragment."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text.strip())


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", cities=config.TARGET_CITIES, categories=CATEGORY_LIST)


@app.route("/search", methods=["POST"])
def search():
    mode = request.form.get("mode")

    if mode == "ai":
        text = request.form.get("free_text", "").strip()
        if not text:
            flash("Please enter a search query.")
            return redirect(url_for("index"))

        parsed = parse_query_with_ai(text, config.TARGET_CITIES, CATEGORY_LIST)
        city, category, limit = parsed.get("city"), parsed.get("category"), parsed.get("limit", 10)

        if not city or not category:
            flash(
                f'Couldn\'t confidently match a city/category from: "{text}". '
                f"Try mentioning a city ({', '.join(config.TARGET_CITIES[:4])}, ...) "
                f"and a business type ({', '.join(CATEGORY_LIST[:4])}, ...), "
                f"or use the structured form instead."
            )
            return redirect(url_for("index"))
    else:
        city = request.form.get("city", "").strip()
        category = request.form.get("category", "").strip()
        try:
            limit = int(request.form.get("limit", 10))
        except ValueError:
            limit = 10

        if not city or not category:
            flash("Please select both a city and a category.")
            return redirect(url_for("index"))

    limit = max(1, min(limit, 50))  # sane bounds

    leads = run_full_pipeline(
        [city], [category], limit,
        run_performance=bool(config.PAGESPEED_API_KEY),
    )

    filename = f"leads_{_safe_filename(city)}_{_safe_filename(category)}_{int(time.time())}.xlsx"
    output_path = os.path.join(config.OUTPUT_DIR, filename)
    export.export_leads_to_excel(leads, output_path)

    return render_template("results.html", leads=leads, city=city, category=category, filename=filename)


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(config.OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
