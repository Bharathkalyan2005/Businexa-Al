"""Dataset routers — profile, clean, analyze, status."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.connection import DatabasePool
from app.db.repositories import DatasetRepository
from app.dependencies import get_db_pool
from app.models.requests import AnalyzeRequest, ProfileRequest
from app.models.responses import DatasetStatusResponse, ProfilingResult
from app.services.analytics.engine import run_full_analysis
from app.services.blob import download_and_parse
from app.services.cleaning import clean_dataframe
from app.services.profiling import profile_dataframe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/{dataset_id}/profile", response_model=ProfilingResult)
async def profile_dataset(
    dataset_id: UUID,
    body: ProfileRequest,
    db: DatabasePool = Depends(get_db_pool),
) -> ProfilingResult:
    """Download the file from Blob storage, profile it, and store column metadata."""
    repo = DatasetRepository(db)

    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found.",
        )

    await repo.update_status(dataset_id, "profiling")

    try:
        df = await download_and_parse(str(body.blob_url))
        result = profile_dataframe(df)
        await repo.insert_columns(dataset_id, result["columns"])
        await repo.update_status(dataset_id, "profiled")

        return ProfilingResult(
            dataset_id=str(dataset_id),
            row_count=result["row_count"],
            duplicate_count=result["duplicate_count"],
            columns=result["columns"],
            quality_score=result["quality_score"],
        )

    except ValueError as exc:
        await repo.update_status(dataset_id, "failed")
        logger.warning("Profiling failed for dataset %s: %s", dataset_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        await repo.update_status(dataset_id, "failed")
        logger.exception("Unexpected error profiling dataset %s", dataset_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while profiling the dataset.",
        ) from exc


@router.post("/{dataset_id}/clean")
async def clean_dataset_endpoint(
    dataset_id: UUID,
    body: ProfileRequest,
    db: DatabasePool = Depends(get_db_pool),
):
    """Clean the dataset: remove duplicates, impute missing values, normalize numbers."""
    repo = DatasetRepository(db)
    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found.",
        )

    await repo.update_status(dataset_id, "cleaning")

    try:
        df = await download_and_parse(str(body.blob_url))
        clean_result = clean_dataframe(df)
        await repo.update_status(dataset_id, "cleaned")

        return {
            "dataset_id": str(dataset_id),
            "status": "cleaned",
            "summary": clean_result["summary"],
        }
    except Exception as exc:
        await repo.update_status(dataset_id, "failed")
        logger.exception("Cleaning failed for dataset %s", dataset_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/{dataset_id}/analyze")
async def analyze_dataset_endpoint(
    dataset_id: UUID,
    body: ProfileRequest,
    db: DatabasePool = Depends(get_db_pool),
):
    """Clean and analyze the dataset: computes KPIs and deterministic insights."""
    repo = DatasetRepository(db)
    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found.",
        )

    await repo.update_status(dataset_id, "analyzing")

    try:
        df = await download_and_parse(str(body.blob_url))
        clean_result = clean_dataframe(df)
        cleaned_df = clean_result["cleaned_df"]

        analysis = run_full_analysis(cleaned_df, body.business_type)
        metrics = analysis["metrics"]
        insights = analysis["insights"]

        snapshot_id = await repo.insert_metrics_snapshot(dataset_id, metrics)
        await repo.insert_insights(dataset_id, insights)
        await repo.update_status(dataset_id, "analyzed")

        return {
            "dataset_id": str(dataset_id),
            "snapshot_id": str(snapshot_id),
            "status": "analyzed",
            "metrics": metrics,
            "insights": insights,
        }
    except Exception as exc:
        await repo.update_status(dataset_id, "failed")
        logger.exception("Analysis failed for dataset %s", dataset_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/{dataset_id}/status", response_model=DatasetStatusResponse)
async def get_dataset_status(
    dataset_id: UUID,
    db: DatabasePool = Depends(get_db_pool),
) -> DatasetStatusResponse:
    """Poll the current status of a dataset."""
    repo = DatasetRepository(db)
    dataset = await repo.get_dataset(dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found.",
        )

    return DatasetStatusResponse(
        dataset_id=str(dataset_id),
        status=dataset["status"],
    )
