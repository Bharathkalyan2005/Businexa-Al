"""Health check router."""

from fastapi import APIRouter

from app.models.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return ok if the service is running."""
    return HealthResponse(status="ok", service="businexa-api")
