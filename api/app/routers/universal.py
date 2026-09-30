"""
Universal Dashboard router — /universal/generate
Orchestrates Stage 1 (profiling) + Stage 2 (LLM spec) in a single endpoint.
Accepts: multipart file upload (CSV/Excel) OR a blob_url string.
"""

from __future__ import annotations

import io
import logging
from typing import Any

import httpx
import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.services.universal.profiler import build_data_profile
from app.services.universal.spec_generator import (
    DashboardSpec,
    generate_dashboard_spec,
    resolve_all_kpi_values,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/universal", tags=["universal-dashboard"])

_MAX_BYTES = 50 * 1024 * 1024  # 50 MB hard cap


# ── Response models ──────────────────────────────────────────────────────────

class KpiCardResolved(BaseModel):
    title: str
    stat_ref: str
    value: Any
    format: str
    icon: str


class ChartSpecOut(BaseModel):
    title: str
    chart_type: str
    x_column: str
    y_columns: list[str]
    aggregate: str
    description: str


class UniversalDashboardResponse(BaseModel):
    # Stage 1
    profile: dict[str, Any]
    # Stage 2
    domain: str
    title: str
    accent_color: str
    kpi_cards: list[KpiCardResolved]
    charts: list[ChartSpecOut]
    used_fallback: bool
    degraded_mode: bool


# ── CSV/Excel parser ─────────────────────────────────────────────────────────

def _parse_bytes(content: bytes, filename: str) -> pd.DataFrame:
    """Parse raw file bytes into a DataFrame based on file extension."""
    name_lower = filename.lower()
    try:
        if name_lower.endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(content))
        else:
            # Try UTF-8, fall back to latin-1
            try:
                return pd.read_csv(io.BytesIO(content), encoding="utf-8")
            except UnicodeDecodeError:
                return pd.read_csv(io.BytesIO(content), encoding="latin-1")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse file '{filename}': {exc}",
        ) from exc


async def _fetch_blob(url: str) -> tuple[bytes, str]:
    """Fetch a file from a blob URL."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        filename = url.split("?")[0].split("/")[-1] or "data.csv"
        return resp.content, filename
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not fetch blob URL: {exc}",
        ) from exc


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=UniversalDashboardResponse)
async def generate_universal_dashboard(
    file: UploadFile | None = File(default=None),
    blob_url: str | None = Form(default=None),
) -> UniversalDashboardResponse:
    """
    Stage 1 + 2 pipeline:
      1. Parse uploaded CSV/Excel or fetch from blob_url
      2. Run deterministic data profiling (no LLM)
      3. Send profile to Claude → validated JSON spec
      4. Resolve all KPI stat_refs to actual values
      5. Return everything the frontend needs to render the dashboard
    """
    # ── 1. Ingest file ───────────────────────────────────────────────────────
    if file is not None:
        content = await file.read()
        if len(content) > _MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds 50 MB limit ({len(content) / 1e6:.1f} MB).",
            )
        filename = file.filename or "upload.csv"
        df = _parse_bytes(content, filename)
    elif blob_url:
        content, filename = await _fetch_blob(blob_url)
        df = _parse_bytes(content, filename)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a file upload or a blob_url.",
        )

    if df.empty and len(df.columns) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded file contains no data or could not be parsed as a table.",
        )

    logger.info("Profiling %d-row x %d-col DataFrame from '%s'", len(df), len(df.columns), filename)

    # ── 2. Stage 1: profile ──────────────────────────────────────────────────
    try:
        profile = build_data_profile(df)
    except Exception as exc:
        logger.exception("Profiling failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profiling failed: {exc}",
        ) from exc

    # ── 3. Stage 2: LLM spec ────────────────────────────────────────────────
    try:
        spec, used_fallback = await generate_dashboard_spec(profile)
    except Exception as exc:
        logger.exception("Spec generation failed, using fallback")
        from app.services.universal.spec_generator import _fallback_dashboard
        spec = _fallback_dashboard(profile)
        used_fallback = True

    # ── 4. Resolve KPI values ────────────────────────────────────────────────
    kpi_resolved = resolve_all_kpi_values(spec, profile)

    # ── 5. Return ────────────────────────────────────────────────────────────
    return UniversalDashboardResponse(
        profile=profile,
        domain=spec.domain,
        title=spec.title,
        accent_color=spec.accent_color,
        kpi_cards=[KpiCardResolved(**k) for k in kpi_resolved],
        charts=[
            ChartSpecOut(
                title=c.title,
                chart_type=c.chart_type,
                x_column=c.x_column,
                y_columns=c.y_columns,
                aggregate=c.aggregate,
                description=c.description,
            )
            for c in spec.charts
        ],
        used_fallback=used_fallback,
        degraded_mode=profile.get("degraded_mode", False),
    )
