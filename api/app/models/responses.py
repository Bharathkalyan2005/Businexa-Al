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


class ProfilingResult(BaseModel):
    dataset_id: str
    row_count: int
    duplicate_count: int
    columns: list[ColumnProfile]
    quality_score: float


class DatasetStatusResponse(BaseModel):
    dataset_id: str
    status: str


class ErrorResponse(BaseModel):
    detail: str
