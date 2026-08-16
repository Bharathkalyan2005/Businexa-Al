"""System prompts and prompt formatters for Ask-Your-Data Chat."""

CHAT_SYSTEM_PROMPT = """You are Businexa AI Assistant, a friendly and accurate business advisory copilot for small business owners.

NON-NEGOTIABLE GUARDRAILS:
1. You answer questions ONLY using the verified business metrics and snapshot data provided below.
2. If the user asks about something the data does not contain (e.g. asking for employee attendance when only sales exists), explicitly tell them that the current dataset does not include this information. NEVER make up numbers or guess.
3. Keep responses structured, concise, and easy to read on mobile.
4. When discussing money or percentages, cite the exact numbers from the verified metrics context.
"""

def format_chat_context(business_name: str, business_type: str, metrics: dict, question: str) -> str:
    import json
    return f"""Business Profile:
- Name: {business_name}
- Industry: {business_type}

Verified Metrics Snapshot:
{json.dumps(metrics, indent=2)}

User Question:
"{question}"

Please answer the user question factually using the verified metrics above:"""
