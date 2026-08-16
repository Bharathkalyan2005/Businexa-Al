"""AI chat router — conversational Q&A on verified business metrics."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db.connection import DatabasePool
from app.dependencies import get_db_pool
from app.services.ai.chat_prompt import CHAT_SYSTEM_PROMPT, format_chat_context
from app.services.ai.gemini import call_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    business_id: UUID
    question: str


class ChatResponse(BaseModel):
    answer: str
    business_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_data(
    body: ChatRequest,
    db: DatabasePool = Depends(get_db_pool),
) -> ChatResponse:
    """Ask a question about your business data — LLM explains verified metrics."""
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

    # Format context and call LLM
    context = format_chat_context(
        business_name=business_row["name"],
        business_type=business_row["business_type"],
        metrics=metrics_json,
        question=body.question,
    )

    answer = await call_llm(CHAT_SYSTEM_PROMPT, context)

    # Persist assistant response
    await db.execute(
        "INSERT INTO chat_messages (business_id, role, content) VALUES ($1, $2, $3)",
        body.business_id,
        "assistant",
        answer,
    )

    return ChatResponse(answer=answer, business_id=str(body.business_id))
