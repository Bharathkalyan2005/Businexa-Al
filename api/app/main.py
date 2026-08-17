"""BizLens API — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.db.connection import DatabasePool
from app.routers import ai, datasets, health, insights, reports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Global rate limiter instance (shared across all routers)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting Businexa API...")
    db = DatabasePool.instance()
    await db.connect()
    logger.info("Database pool ready.")
    yield
    await db.disconnect()
    logger.info("Database pool closed. Goodbye.")


app = FastAPI(
    title="Businexa API",
    description="Analytics & AI backend for Businexa AI",
    version="0.1.0",
    lifespan=lifespan,
    # Disable docs in production by checking env
    docs_url="/docs" if not settings.cors_origins.startswith("https://") else None,
    redoc_url=None,
)

# Attach rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# CORS — locked to explicit origins only, never wildcard in production
_cors_origins = settings.cors_origin_list
if not _cors_origins:
    # Local dev fallback only — never reaches production if CORS_ORIGINS is set
    _cors_origins = ["http://localhost:3000"]
    logger.warning("CORS_ORIGINS is not set; defaulting to localhost:3000 only.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Internal-Key"],
)

# Routers
app.include_router(health.router)
app.include_router(datasets.router)
app.include_router(insights.router)
app.include_router(ai.router)
app.include_router(reports.router)
