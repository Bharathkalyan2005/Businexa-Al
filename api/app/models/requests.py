"""Pydantic request models for the API."""

from uuid import UUID

from pydantic import BaseModel, HttpUrl


class ProfileRequest(BaseModel):
    """Body for POST /datasets/{id}/profile."""

    blob_url: HttpUrl
    business_type: str


class CleanRequest(BaseModel):
    """Body for POST /datasets/{id}/clean (Phase 3)."""

    pass


class AnalyzeRequest(BaseModel):
    """Body for POST /datasets/{id}/analyze (Phase 3)."""

    business_type: str
