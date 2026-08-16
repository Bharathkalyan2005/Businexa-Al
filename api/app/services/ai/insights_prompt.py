"""System prompts and prompt formatters for AI insights generation."""

INSIGHTS_SYSTEM_PROMPT = """You are Businexa AI, a senior business analyst explaining verified sales numbers to a small business owner.

CORE RULES:
1. NEVER invent, guess, or calculate numbers not explicitly present in the provided verified JSON.
2. Translate the precomputed metrics and findings into clear, empathetic, and actionable business advice.
3. Highlight 2-3 high-impact next actions the business owner can take immediately.
4. Keep the tone professional, direct, and concise (under 250 words total). Avoid buzzwords and unnecessary jargon.
"""

def format_insights_input(metrics: dict, deterministic_insights: list[dict]) -> str:
    import json
    return f"""Here are the precomputed verified metrics for the business:
{json.dumps(metrics, indent=2)}

Deterministic rule triggers detected:
{json.dumps(deterministic_insights, indent=2)}

Please provide a concise plain-language summary and 2-3 specific action items for the owner."""
