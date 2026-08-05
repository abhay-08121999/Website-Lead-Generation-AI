"""
query_parser.py
----------------
Turns a free-text query like "find beauty salons without website in
Jaipur" into structured {city, category, limit} params the pipeline
can run on.

Uses Groq's free-tier API (llama-3.3-70b-versatile) — same LLM
provider used elsewhere in this project's ecosystem. If no Groq key
is configured, or the call fails for any reason, falls back to
simple keyword matching against the known city/category lists so the
feature still works without any AI key.
"""

import json
import re
import requests
from typing import List, Dict, Optional

import config

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def parse_query_fallback(text: str, cities: List[str], categories: List[str]) -> Dict:
    """Simple, dependency-free keyword matcher. Used when no AI key is set or the AI call fails."""
    text_lower = text.lower()

    matched_city = next((c for c in cities if c.lower() in text_lower), None)
    matched_category = next((cat for cat in categories if cat.lower() in text_lower), None)

    limit_match = re.search(r"\b(\d{1,3})\b", text)
    limit = int(limit_match.group(1)) if limit_match else 10

    return {"city": matched_city, "category": matched_category, "limit": limit}


def parse_query_with_ai(text: str, cities: List[str], categories: List[str]) -> Dict:
    """
    Returns: {"city": str or None, "category": str or None, "limit": int}
    Falls back to keyword matching if no API key or on any error.
    """
    if not config.GROQ_API_KEY:
        return parse_query_fallback(text, cities, categories)

    system_prompt = (
        "You convert a natural-language business-lead search request into structured JSON.\n"
        f"Available cities (pick the closest match, or null if none fit): {cities}\n"
        f"Available categories (pick the closest match, or null if none fit): {categories}\n"
        'Respond with ONLY valid JSON, no markdown fences, no explanation: '
        '{"city": "<city or null>", "category": "<category or null>", "limit": <integer, default 10>}'
    )

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "temperature": 0,
                "max_tokens": 150,
            },
            timeout=15,
        )
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if the model added them anyway
        content = re.sub(r"^```(json)?|```$", "", content, flags=re.MULTILINE).strip()

        parsed = json.loads(content)
        city = parsed.get("city") or None
        category = parsed.get("category") or None
        limit = int(parsed.get("limit") or 10)

        # Guard against the model hallucinating a city/category not in our lists
        if city and city not in cities:
            city = next((c for c in cities if c.lower() == str(city).lower()), None)
        if category and category not in categories:
            category = next((c for c in categories if c.lower() == str(category).lower()), None)

        return {"city": city, "category": category, "limit": limit}

    except Exception as e:
        print(f"[WARN] AI query parsing failed ({e}) — falling back to keyword matching.")
        return parse_query_fallback(text, cities, categories)
