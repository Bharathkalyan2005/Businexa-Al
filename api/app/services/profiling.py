"""Data profiling service — detect column types, roles, and quality."""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

from app.services.column_roles import detect_column_roles, suggest_ui_confirmations

logger = logging.getLogger(__name__)


def _is_date_column(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if pd.api.types.is_numeric_dtype(series):
        return False

    non_null = series.dropna().astype(str).str.strip()
    non_null = non_null[non_null != ""]
    if len(non_null) == 0:
        return False

    sample = non_null.head(50)
    has_date_separators = sample.apply(
        lambda s: any(sep in s for sep in ["-", "/", " ", ".", ","])
    )
    if has_date_separators.sum() / len(sample) < 0.4:
        return False

    parsed = pd.to_datetime(sample, errors="coerce")
    success_rate = parsed.notna().sum() / len(sample)
    return success_rate >= 0.6


def _is_currency_column(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return False

    non_null = series.dropna().astype(str).str.strip()
    if len(non_null) == 0:
        return False

    sample = non_null.head(50)
    currency_pattern = re.compile(r"^[\$€£¥₹]?\s*-?\s*[\d,]+\.?\d*$")
    matches = sample.apply(lambda x: bool(currency_pattern.match(x)))
    return matches.sum() / len(sample) >= 0.6


def _detect_column_type(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if _is_date_column(series):
        return "date"
    if _is_currency_column(series):
        return "currency"

    non_null = series.dropna()
    if len(non_null) > 0:
        unique_ratio = series.nunique() / len(non_null)
        if unique_ratio < 0.5 or series.nunique() <= 50:
            return "categorical"
        return "text"

    return "unknown"


def profile_dataframe(
    df: pd.DataFrame,
    business_type: str = "other",
) -> dict[str, Any]:
    """Profile a DataFrame: types, roles, quality score, and viability."""
    if df.empty and len(df.columns) == 0:
        raise ValueError("Cannot profile an empty DataFrame with no columns.")

    row_count = len(df)
    duplicate_count = int(df.duplicated().sum())

    role_result = detect_column_roles(df, business_type)
    role_by_column = {
        c["column_name"]: c for c in role_result["columns"]
    }
    ui_confirmations = suggest_ui_confirmations(
        role_result["role_mapping"],
        role_result["columns"],
    )

    columns: list[dict[str, Any]] = []
    total_missing_pct = 0.0

    for col_name in df.columns:
        col_str = str(col_name)
        series = df[col_name]
        detected_type = _detect_column_type(series)
        missing_count = int(series.isna().sum())
        missing_pct = (missing_count / row_count * 100) if row_count > 0 else 0.0
        total_missing_pct += missing_pct

        role_info = role_by_column.get(col_str, {})
        columns.append({
            "column_name": col_str,
            "detected_type": detected_type,
            "missing_count": missing_count,
            "missing_pct": round(missing_pct, 2),
            "detected_role": role_info.get("detected_role", "unassigned"),
            "role_confidence": role_info.get("role_confidence", 0.0),
            "role_reason": role_info.get("reason", ""),
            "role_scores": role_info.get("role_scores", {}),
            "excluded": role_info.get("excluded", False),
        })

    num_columns = len(columns)
    avg_missing_pct = (total_missing_pct / num_columns) if num_columns > 0 else 0.0
    duplicate_pct = (duplicate_count / row_count * 100) if row_count > 0 else 0.0
    unknown_count = sum(1 for c in columns if c["detected_type"] == "unknown")
    type_unknown_pct = (unknown_count / num_columns * 100) if num_columns > 0 else 0.0

    raw_score = 100.0 - (avg_missing_pct * 0.5 + duplicate_pct * 0.3 + type_unknown_pct * 0.2)
    quality_score = round(max(0.0, min(100.0, raw_score)), 1)

    return {
        "row_count": row_count,
        "duplicate_count": duplicate_count,
        "columns": columns,
        "quality_score": quality_score,
        "role_mapping": role_result["role_mapping"],
        "dashboard_viable": role_result["dashboard_viable"],
        "dashboard_error": role_result["dashboard_error"],
        "excluded_columns": role_result["excluded_columns"],
        "pipeline_log": role_result["pipeline_log"],
        "ui_confirmations": ui_confirmations,
    }
