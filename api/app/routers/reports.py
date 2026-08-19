"""PDF Report generation router."""

from __future__ import annotations

import json
import logging
import os
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.db.connection import DatabasePool
from app.dependencies import get_db_pool
from app.services.ai.gemini import call_llm
from app.services.reports.pdf_builder import build_pdf_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])
limiter = Limiter(key_func=get_remote_address)


class GenerateReportRequest(BaseModel):
    business_id: UUID
    dataset_id: UUID


class ReportResponse(BaseModel):
    id: str
    business_id: str
    dataset_id: str
    pdf_url: str
    generated_at: str


async def _upload_pdf_to_blob(pdf_bytes: bytes, filename: str) -> str:
    """Upload PDF bytes to Vercel Blob and return public URL.
    Falls back to a data: URL if BLOB_READ_WRITE_TOKEN is not set (local dev).
    """
    token = settings.blob_read_write_token
    if not token or "dummy" in token.lower():
        import base64
        logger.info("Blob token not configured — using data URL for local dev.")
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        return f"data:application/pdf;base64,{b64}"

    upload_url = f"https://blob.vercel-storage.com/{filename}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.put(
            upload_url,
            content=pdf_bytes,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/pdf",
                "x-vercel-blob-content-type": "application/pdf",
            },
        )
        if resp.status_code not in (200, 201):
            logger.warning("Blob upload failed (%s): %s", resp.status_code, resp.text[:200])
            # Graceful fallback so report generation doesn't completely fail
            import base64
            b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return f"data:application/pdf;base64,{b64}"

        data = resp.json()
        return data.get("url", data.get("downloadUrl", ""))


@router.post("/generate", response_model=ReportResponse)
@limiter.limit(f"{settings.rate_limit_reports}/minute")
async def generate_report_endpoint(
    request: Request,
    body: GenerateReportRequest,
    db: DatabasePool = Depends(get_db_pool),
) -> ReportResponse:
    """Generate a PDF performance report for a business."""
    # Fetch business
    b_row = await db.fetch_one(
        "SELECT name, business_type FROM businesses WHERE id = $1",
        body.business_id,
    )
    if not b_row:
        raise HTTPException(status_code=404, detail="Business not found.")

    # Fetch snapshot
    s_row = await db.fetch_one(
        "SELECT raw_json FROM metrics_snapshots WHERE dataset_id = $1 ORDER BY computed_at DESC LIMIT 1",
        body.dataset_id,
    )
    raw_val = s_row["raw_json"] if s_row and s_row["raw_json"] else {}
    if isinstance(raw_val, str):
        try:
            metrics = json.loads(raw_val)
        except Exception:
            metrics = {}
    elif isinstance(raw_val, dict):
        metrics = raw_val
    else:
        metrics = {}

    # Fetch insights
    i_rows = await db.fetch_all(
        "SELECT insight_text FROM insights WHERE dataset_id = $1",
        body.dataset_id,
    )
    insights = [r["insight_text"] for r in i_rows]

    # Generate executive summary via LLM (max 400 tokens — it's 2 sentences)
    exec_summary_prompt = (
        f"Write a professional 2-sentence executive summary for {b_row['name']} "
        f"({b_row['business_type']}) based on these numbers: {json.dumps(metrics)}"
    )
    exec_summary = await call_llm(
        "You are a business analyst writing an executive summary.",
        exec_summary_prompt,
        max_tokens=400,
    )

    # Build PDF bytes
    pdf_bytes = build_pdf_report(
        business_name=b_row["name"],
        business_type=b_row["business_type"],
        metrics=metrics,
        insights=insights,
        narrative_sections={"executive_summary": exec_summary},
    )

    # Upload PDF to Blob (not storing base64 in DB)
    safe_name = b_row["name"].lower().replace(" ", "-")
    pdf_filename = f"reports/{body.business_id}/{safe_name}-report.pdf"
    pdf_url = await _upload_pdf_to_blob(pdf_bytes, pdf_filename)

    # Insert report metadata (URL only — never raw bytes in DB)
    row = await db.fetch_one(
        "INSERT INTO reports (business_id, dataset_id, pdf_url) VALUES ($1, $2, $3) "
        "RETURNING id, generated_at",
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
        "SELECT id, business_id, dataset_id, pdf_url, generated_at "
        "FROM reports WHERE business_id = $1 ORDER BY generated_at DESC",
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
