"""PDF Report generation router."""

from __future__ import annotations

import base64
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.db.connection import DatabasePool
from app.dependencies import get_db_pool
from app.services.ai.gemini import call_llm
from app.services.reports.pdf_builder import build_pdf_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    business_id: UUID
    dataset_id: UUID


class ReportResponse(BaseModel):
    id: str
    business_id: str
    dataset_id: str
    pdf_url: str
    generated_at: str


@router.post("/generate", response_model=ReportResponse)
async def generate_report_endpoint(
    body: GenerateReportRequest,
    db: DatabasePool = Depends(get_db_pool),
) -> ReportResponse:
    """Generate a PDF performance report for a business."""
    # Fetch business
    b_row = await db.fetch_one("SELECT name, business_type FROM businesses WHERE id = $1", body.business_id)
    if not b_row:
        raise HTTPException(status_code=404, detail="Business not found.")

    # Fetch snapshot
    s_row = await db.fetch_one("SELECT raw_json FROM metrics_snapshots WHERE dataset_id = $1 ORDER BY computed_at DESC LIMIT 1", body.dataset_id)
    metrics = json.loads(s_row["raw_json"]) if s_row and s_row["raw_json"] else {}

    # Fetch insights
    i_rows = await db.fetch_all("SELECT insight_text FROM insights WHERE dataset_id = $1", body.dataset_id)
    insights = [r["insight_text"] for r in i_rows]

    # Generate executive summary via LLM
    exec_summary_prompt = f"Write a professional 2-sentence executive summary for {b_row['name']} ({b_row['business_type']}) based on these numbers: {json.dumps(metrics)}"
    exec_summary = await call_llm("You are a business analyst writing an executive summary.", exec_summary_prompt)

    # Build PDF bytes
    pdf_bytes = build_pdf_report(
        business_name=b_row["name"],
        business_type=b_row["business_type"],
        metrics=metrics,
        insights=insights,
        narrative_sections={"executive_summary": exec_summary},
    )

    # Store base64 data URL in database
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_url = f"data:application/pdf;base64,{pdf_b64}"

    # Insert into reports table
    row = await db.fetch_one(
        "INSERT INTO reports (business_id, dataset_id, pdf_url) VALUES ($1, $2, $3) RETURNING id, generated_at",
        body.business_id,
        body.dataset_id,
        pdf_url,
    )

    return ReportResponse(
        id=str(row["id"]),
        business_id=str(body.business_id),
        dataset_id=str(body.dataset_id),
        pdf_url=pdf_url,
        generated_at=str(row["generated_at"]),
    )


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    business_id: UUID,
    db: DatabasePool = Depends(get_db_pool),
) -> list[ReportResponse]:
    """List past generated reports for a business."""
    rows = await db.fetch_all(
        "SELECT id, business_id, dataset_id, pdf_url, generated_at FROM reports WHERE business_id = $1 ORDER BY generated_at DESC",
        business_id,
    )
    return [
        ReportResponse(
            id=str(r["id"]),
            business_id=str(r["business_id"]),
            dataset_id=str(r["dataset_id"]),
            pdf_url=r["pdf_url"],
            generated_at=str(r["generated_at"]),
        )
        for r in rows
    ]
