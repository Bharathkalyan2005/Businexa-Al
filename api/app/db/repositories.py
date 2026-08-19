"""Database repositories — read/write helpers for datasets and columns."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.db.connection import DatabasePool


class DatasetRepository:
    """All dataset-related database operations."""

    def __init__(self, db: DatabasePool) -> None:
        self._db = db

    async def get_dataset(self, dataset_id: UUID) -> dict[str, Any] | None:
        """Fetch a single dataset by ID."""
        row = await self._db.fetch_one(
            "SELECT id, business_id, filename, storage_url, status, uploaded_at "
            "FROM datasets WHERE id = $1",
            dataset_id,
        )
        if row is None:
            return None
        return dict(row)

    async def update_status(self, dataset_id: UUID, status: str) -> None:
        """Update the status column of a dataset."""
        await self._db.execute(
            "UPDATE datasets SET status = $1 WHERE id = $2",
            status,
            dataset_id,
        )

    async def insert_columns(
        self,
        dataset_id: UUID,
        columns: list[dict[str, Any]],
    ) -> None:
        """Bulk-insert profiled column metadata, replacing any previous results."""
        # Remove old column records first (re-profiling a dataset)
        await self._db.execute(
            "DELETE FROM dataset_columns WHERE dataset_id = $1",
            dataset_id,
        )

        if not columns:
            return

        values_clauses: list[str] = []
        args: list[Any] = []
        for i, col in enumerate(columns):
            offset = i * 5
            values_clauses.append(
                f"(${offset + 1}, ${offset + 2}, ${offset + 3}, ${offset + 4}, ${offset + 5})"
            )
            args.extend([
                dataset_id,
                col["column_name"],
                col["detected_type"],
                str(col["missing_count"]),
                str(round(col["missing_pct"], 2)),
            ])

        sql = (
            "INSERT INTO dataset_columns "
            "(dataset_id, column_name, detected_type, missing_count, missing_pct) "
            f"VALUES {', '.join(values_clauses)}"
        )
        await self._db.execute(sql, *args)

    async def insert_metrics_snapshot(
        self,
        dataset_id: UUID,
        metrics: dict[str, Any],
    ) -> UUID:
        """Insert a metrics snapshot and return its ID."""
        row = await self._db.fetch_one(
            "INSERT INTO metrics_snapshots "
            "(dataset_id, revenue, profit, orders, growth_pct, top_product, raw_json) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7) "
            "RETURNING id",
            dataset_id,
            str(metrics.get("revenue")) if metrics.get("revenue") is not None else None,
            str(metrics.get("profit")) if metrics.get("profit") is not None else None,
            str(metrics.get("orders")) if metrics.get("orders") is not None else None,
            str(metrics.get("growth_pct")) if metrics.get("growth_pct") is not None else None,
            metrics.get("top_product"),
            json.dumps(metrics),
        )
        return row["id"]  # type: ignore[index]

    async def insert_insights(
        self,
        dataset_id: UUID,
        insights: list[dict[str, str]],
    ) -> None:
        """Bulk-insert deterministic insight strings."""
        if not insights:
            return

        values_clauses: list[str] = []
        args: list[Any] = []
        for i, insight in enumerate(insights):
            offset = i * 3
            values_clauses.append(f"(${offset + 1}, ${offset + 2}, ${offset + 3})")
            args.extend([
                dataset_id,
                insight["text"],
                insight["category"],
            ])

        sql = f"INSERT INTO insights (dataset_id, insight_text, category) VALUES {', '.join(values_clauses)}"
        await self._db.execute(sql, *args)

    async def get_columns(self, dataset_id: UUID) -> list[dict[str, Any]]:
        """Fetch all profiled columns for a dataset."""
        rows = await self._db.fetch_all(
            "SELECT id, column_name, detected_type, missing_count, missing_pct "
            "FROM dataset_columns WHERE dataset_id = $1 "
            "ORDER BY column_name",
            dataset_id,
        )
        return [dict(r) for r in rows]
