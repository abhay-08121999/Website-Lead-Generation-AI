"""
outreach_generator.py
----------------------
Drafts a short, personalized cold-outreach message for a qualified
lead, using Groq to reference the SPECIFIC reason they were flagged
(not a generic template) — "your site hasn't updated since 2023" is
a much stronger opener than "I noticed you might need a website".

Falls back to a simple (still personalized, just less natural)
template if no Groq key is configured — the feature never breaks,
it just loses the AI polish.
"""

import requests
from typing import Dict

import config

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _template_fallback(business_name: str, category: str, lead_category: str, lead_reason: str) -> str:
    if lead_category == "NO_WEBSITE":
        hook = f"I noticed {business_name} doesn't have a website listed yet"
    else:
        # lead_reason looks like "Underperforming site: low PageSpeed score (35/100), no HTTPS"
        detail = lead_reason.split(":", 1)[-1].strip() if ":" in lead_reason else lead_reason
        hook = f"I came across {business_name} and noticed a few things about the website ({detail})"

    return (
        f"Hi, this is [Your Name] — a web developer based in [Your City].\n\n"
        f"{hook}, and thought I'd reach out. I help local {category} businesses "
        f"get a clean, fast, mobile-friendly website that actually brings in customers.\n\n"
        f"Would you be open to a quick chat about what a new site could do for {business_name}?\n\n"
        f"Best,\n[Your Name]"
    )


def generate_outreach_message(
    business_name: str,
    category: str,
    city: str,
    lead_category: str,
    lead_reason: str,
    tone: str = "friendly",
) -> Dict:
    """
    Returns: {"message": str, "source": "ai" | "template", "error": str or None}
    """
    if not config.GROQ_API_KEY:
        return {
            "message": _template_fallback(business_name, category, lead_category, lead_reason),
            "source": "template",
            "error": None,
        }

    system_prompt = (
        "You write short, warm, non-pushy cold-outreach messages from a freelance "
        "web developer reaching out to small local businesses. Rules:\n"
        "- 3-5 sentences, plain everyday language, no corporate jargon or hype\n"
        "- Naturally reference the SPECIFIC website issue given — phrase it like a "
        "helpful observation, not a report or a sales pitch\n"
        "- Offer to help without pressure — end with a soft, open question\n"
        "- Sign off exactly as '[Your Name]'\n"
        "- Output ONLY the message body — no subject line, no markdown, no preamble"
    )

    user_prompt = (
        f"Business name: {business_name}\n"
        f"Business type: {category}\n"
        f"City: {city}\n"
        f"Specific issue found: {lead_reason}\n"
        f"Tone: {tone}\n\n"
        "Write the outreach message now."
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
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=20,
        )
        data = resp.json()
        message = data["choices"][0]["message"]["content"].strip()
        if not message:
            raise ValueError("Empty response from Groq")
        return {"message": message, "source": "ai", "error": None}

    except Exception as e:
        print(f"[WARN] AI outreach generation failed ({e}) — falling back to template.", flush=True)
        return {
            "message": _template_fallback(business_name, category, lead_category, lead_reason),
            "source": "template",
            "error": str(e),
        }
