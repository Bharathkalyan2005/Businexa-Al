"""Pydantic response models for the API."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class ColumnProfile(BaseModel):
    column_name: str
    detected_type: str
    missing_count: int
    missing_pct: float
    detected_role: str = "unassigned"
    role_confidence: float = 0.0
    role_reason: str = ""
    role_scores: dict[str, float] = {}
    excluded: bool = False


class ProfilingResult(BaseModel):
    dataset_id: str
    row_count: int
    duplicate_count: int
    columns: list[ColumnProfile]
    quality_score: float
    role_mapping: dict[str, str | None] = {}
    dashboard_viable: bool = False
    dashboard_error: str | None = None
    excluded_columns: list[dict[str, str]] = []
    pipeline_log: list[dict[str, str]] = []
    ui_confirmations: list[dict] = []


class DatasetStatusResponse(BaseModel):
    dataset_id: str
    status: str


class ErrorResponse(BaseModel):
    detail: str
