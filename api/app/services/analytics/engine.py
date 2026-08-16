"""Analytics orchestrator — ties profiling, cleaning, metrics, and insights together."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.services.analytics.metrics import compute_metrics
from app.services.analytics.insights_rules import generate_insights

logger = logging.getLogger(__name__)


def run_full_analysis(
    df: pd.DataFrame,
    business_type: str,
) -> dict[str, Any]:
    """Run the complete analytics pipeline on a cleaned DataFrame.

    Returns:
        dict with 'metrics' and 'insights' keys.
    """
    # Compute metrics
    metrics = compute_metrics(df, business_type)

    # Generate deterministic insights
    insights = generate_insights(metrics)

    return {
        "metrics": metrics,
        "insights": insights,
    }
