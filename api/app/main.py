"""BizLens API — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.connection import DatabasePool
from app.routers import ai, datasets, health, insights, reports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(datasets.router)
app.include_router(insights.router)
app.include_router(ai.router)
app.include_router(reports.router)
