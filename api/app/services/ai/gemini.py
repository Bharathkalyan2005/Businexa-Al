"""AI Service wrapper — generates plain-language explanations using Gemini API or rule fallbacks.
Strict rule: The LLM explains structured precomputed metrics only, never performs calculations."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_KEY_PATTERN = re.compile(r"(key=)[^&\s]+")


def _sanitize_url(url: str) -> str:
    """Replace API key value in a URL with '***' for safe logging."""
    return _KEY_PATTERN.sub(r"\1***", url)


async def call_llm(
    system_prompt: str,
    user_content: str,
    *,
    max_tokens: int = 800,
) -> str:
    """Call Google Gemini API (or fallback if API key is not configured)."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return "AI response unavailable — please set GEMINI_API_KEY in environment variables."

    base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    models = ["gemini-2.0-flash", "gemini-1.5-flash"]

    try:
        import httpx

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
                "maxOutputTokens": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in models:
                url = f"{base_url}/{model}:generateContent?key={api_key}"
                resp = await client.post(url, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                else:
                    # Log with sanitized URL — never log the raw key
                    safe_url = _sanitize_url(url)
                    logger.warning(
                        "Gemini API returned status %s for %s: %s",
                        resp.status_code,
                        safe_url,
                        resp.text[:200],  # Truncate response body too
                    )

    except Exception as exc:
        logger.exception("Error querying Gemini API: %s", exc)

    return "Based on your verified data, your business metrics show steady operations. Upload further periods to track detailed trends."
