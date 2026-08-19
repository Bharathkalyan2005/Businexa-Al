"""FastAPI dependency injection — API key auth and database sessions."""

from fastapi import Depends, Header, HTTPException, status

from app.config import settings
from app.db.connection import DatabasePool


async def verify_api_key(
    x_internal_api_key: str | None = Header(None, alias="X-Internal-Api-Key"),
    x_internal_key: str | None = Header(None, alias="X-Internal-Key"),
) -> str:
    """Reject requests without a valid internal API key."""
    provided_key = x_internal_api_key or x_internal_key
    if not provided_key or provided_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
    return provided_key


async def get_db_pool(
    _api_key: str = Depends(verify_api_key),
) -> DatabasePool:
    """Return the shared database connection pool (after auth check)."""
    return DatabasePool.instance()
