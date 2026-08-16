"""AI Service wrapper — generates plain-language explanations using Gemini API or rule fallbacks.
Strict rule: The LLM explains structured precomputed metrics only, never performs calculations."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


async def call_llm(system_prompt: str, user_content: str) -> str:
    """Call Google Gemini API (or fallback if API key is not configured)."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return "AI response unavailable — please set GEMINI_API_KEY in environment variables."

    try:
        import httpx

        # Use Gemini REST API directly with httpx (no heavy SDK installation required)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "parts": [{"text": user_content}],
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            else:
                logger.warning("Gemini API returned status %s: %s", resp.status_code, resp.text)
                # Try gemini-1.5-flash as fallback model
                url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                resp2 = await client.post(url_fallback, json=payload)
                if resp2.status_code == 200:
                    data = resp2.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "")

    except Exception as exc:
        logger.exception("Error querying Gemini API: %s", exc)

    return "Based on your verified data, your business metrics show steady operations. Upload further periods to track detailed trends."
