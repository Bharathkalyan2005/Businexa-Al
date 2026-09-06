"""Pydantic request models for the API."""

from pydantic import BaseModel, Field


class ProfileRequest(BaseModel):
    """Body for POST /datasets/{id}/profile."""

    blob_url: str
    business_type: str = "other"


class AnalyzeRequest(BaseModel):
    """Body for POST /datasets/{id}/analyze."""

    blob_url: str
    business_type: str = "other"
    column_mapping: dict[str, str | None] | None = Field(
        default=None,
        description="User-confirmed role → column name mapping",
    )
