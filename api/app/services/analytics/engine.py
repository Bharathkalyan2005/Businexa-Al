"""Analytics orchestrator — ties cleaning, metrics, and insights together."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.services.analytics.insights_rules import generate_insights
from app.services.analytics.metrics import compute_metrics
from app.services.column_roles import check_dashboard_viability, merge_role_mapping

logger = logging.getLogger(__name__)


def run_full_analysis(
    df: pd.DataFrame,
    business_type: str,
    role_mapping: dict[str, str | None] | None = None,
    auto_role_mapping: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Run analytics using confirmed or auto-detected column roles."""
    mapping = merge_role_mapping(auto_role_mapping or {}, role_mapping)
    viable, error = check_dashboard_viability(mapping)

    metrics = compute_metrics(
        df,
        business_type,
        role_mapping=role_mapping,
        auto_role_mapping=auto_role_mapping,
    )

    if not viable:
        return {
            "metrics": metrics,
            "insights": [],
            "dashboard_viable": False,
            "dashboard_error": error,
        }

    insights = generate_insights(metrics)

    return {
        "metrics": metrics,
        "insights": insights,
        "dashboard_viable": True,
        "dashboard_error": None,
    }
