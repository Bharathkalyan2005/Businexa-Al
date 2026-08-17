"""AI chat router — conversational Q&A on verified business metrics."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.db.connection import DatabasePool
from app.dependencies import get_db_pool
from app.services.ai.chat_prompt import CHAT_SYSTEM_PROMPT, format_chat_context
from app.services.ai.gemini import call_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])
limiter = Limiter(key_func=get_remote_address)

_CHAT_HISTORY_LIMIT = 10  # Only pass last N messages to LLM to control token cost


def _validate_internal_key(request: Request) -> None:
    """Reject requests that don't present the correct internal API key."""
    key = request.headers.get("X-Internal-Key", "")
    if key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid internal API key.",
        )


class ChatRequest(BaseModel):
    business_id: UUID
    question: str


class ChatResponse(BaseModel):
    answer: str
    business_id: str


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.rate_limit_chat}/minute")
async def chat_with_data(
    request: Request,
    body: ChatRequest,
    db: DatabasePool = Depends(get_db_pool),
) -> ChatResponse:
    """Ask a question about your business data — LLM explains verified metrics."""
    _validate_internal_key(request)

    # Fetch business profile
    business_row = await db.fetch_one(
        "SELECT id, name, business_type FROM businesses WHERE id = $1",
        body.business_id,
    )
    if not business_row:
        raise HTTPException(status_code=404, detail="Business not found.")

    # Fetch latest dataset for this business
    dataset_row = await db.fetch_one(
        "SELECT id FROM datasets WHERE business_id = $1 ORDER BY uploaded_at DESC LIMIT 1",
        body.business_id,
    )

    metrics_json: dict = {}
    if dataset_row:
        snapshot_row = await db.fetch_one(
            "SELECT raw_json FROM metrics_snapshots WHERE dataset_id = $1 ORDER BY computed_at DESC LIMIT 1",
            dataset_row["id"],
        )
        if snapshot_row and snapshot_row["raw_json"]:
            if isinstance(snapshot_row["raw_json"], str):
                metrics_json = json.loads(snapshot_row["raw_json"])
            else:
                metrics_json = snapshot_row["raw_json"]

    # Persist user question
    await db.execute(
        "INSERT INTO chat_messages (business_id, role, content) VALUES ($1, $2, $3)",
        body.business_id,
        "user",
        body.question,
    )

    # Fetch last N messages for context (cap to control token cost)
    history_rows = await db.fetch_all(
        "SELECT role, content FROM chat_messages WHERE business_id = $1 "
        "ORDER BY created_at DESC LIMIT $2",
        body.business_id,
        _CHAT_HISTORY_LIMIT,
    )
    recent_history = list(reversed([dict(r) for r in history_rows]))

    # Format context and call LLM
    context = format_chat_context(
        business_name=business_row["name"],
        business_type=business_row["business_type"],
        metrics=metrics_json,
        question=body.question,
        history=recent_history,
    )

    answer = await call_llm(CHAT_SYSTEM_PROMPT, context, max_tokens=600)

    # Persist assistant response
    await db.execute(
        "INSERT INTO chat_messages (business_id, role, content) VALUES ($1, $2, $3)",
        body.business_id,
        "assistant",
        answer,
    )

    return ChatResponse(answer=answer, business_id=str(body.business_id))
