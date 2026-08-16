"""AI insights router — explains verified metrics in plain language."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.connection import DatabasePool
from app.dependencies import get_db_pool
from app.services.ai.gemini import call_llm
from app.services.ai.insights_prompt import INSIGHTS_SYSTEM_PROMPT, format_insights_input

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])


class InsightsResponse(BaseModel):
    business_id: str
    summary_text: str
    deterministic_insights: list[dict]


@router.get("/{business_id}", response_model=InsightsResponse)
async def get_enhanced_insights(
    business_id: UUID,
    db: DatabasePool = Depends(get_db_pool),
) -> InsightsResponse:
    """Fetch latest precomputed metrics and generate LLM narrative explanation."""
    dataset_row = await db.fetch_one(
        "SELECT id FROM datasets WHERE business_id = $1 ORDER BY uploaded_at DESC LIMIT 1",
        business_id,
    )
    if not dataset_row:
        raise HTTPException(status_code=404, detail="No datasets found for this business.")

    dataset_id = dataset_row["id"]

    # Fetch snapshot
    snapshot_row = await db.fetch_one(
        "SELECT raw_json FROM metrics_snapshots WHERE dataset_id = $1 ORDER BY computed_at DESC LIMIT 1",
        dataset_id,
    )
    metrics = json.loads(snapshot_row["raw_json"]) if snapshot_row and snapshot_row["raw_json"] else {}

    # Fetch deterministic insights
    insights_rows = await db.fetch_all(
        "SELECT insight_text, category FROM insights WHERE dataset_id = $1",
        dataset_id,
    )
    insights_list = [{"text": r["insight_text"], "category": r["category"]} for r in insights_rows]

    # Generate LLM explanation from verified numbers
    prompt_input = format_insights_input(metrics, insights_list)
    llm_summary = await call_llm(INSIGHTS_SYSTEM_PROMPT, prompt_input)

    return InsightsResponse(
        business_id=str(business_id),
        summary_text=llm_summary,
        deterministic_insights=insights_list,
    )
