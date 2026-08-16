"""Data profiling service — detect column types, count missing values, compute quality."""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _is_date_column(series: pd.Series) -> bool:
    """Heuristic: try to parse a sample as dates (only for string/object series)."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    if pd.api.types.is_numeric_dtype(series):
        return False

    non_null = series.dropna().astype(str)
    if len(non_null) == 0:
        return False

    # Check if strings contain date-like separators (-, /, :)
    sample = non_null.head(50)
    has_date_separators = sample.apply(lambda s: any(sep in s for sep in ["-", "/", " ", ","]))
    if has_date_separators.sum() / len(sample) < 0.6:
        return False

    try:
        parsed = pd.to_datetime(sample, errors="coerce")
        success_rate = parsed.notna().sum() / len(sample)
        return success_rate >= 0.7
    except Exception:
        return False


def _is_currency_column(series: pd.Series) -> bool:
    """Heuristic: values look like $1,234.56 or €100."""
    if pd.api.types.is_numeric_dtype(series):
        return False

    non_null = series.dropna().astype(str)
    if len(non_null) == 0:
        return False

    sample = non_null.head(50)
    currency_pattern = re.compile(r"^[\$€£¥₹]?\s*-?\s*[\d,]+\.?\d*$")
    matches = sample.apply(lambda x: bool(currency_pattern.match(x.strip())))
    return matches.sum() / len(sample) >= 0.7


def _detect_column_type(series: pd.Series) -> str:
    """Detect the semantic type of a column."""
    # 1. Native datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    # 2. Native numeric (int/float)
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # 3. String-encoded dates
    if _is_date_column(series):
        return "date"

    # 4. String-encoded currency
    if _is_currency_column(series):
        return "currency"

    # 5. Categorical vs freeform text
    non_null = series.dropna()
    if len(non_null) > 0:
        unique_ratio = series.nunique() / len(non_null)
        if unique_ratio < 0.5 or series.nunique() <= 50:
            return "categorical"
        return "text"

    return "unknown"


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Profile a DataFrame and return structured results."""
    if df.empty and len(df.columns) == 0:
        raise ValueError("Cannot profile an empty DataFrame with no columns.")

    row_count = len(df)
    duplicate_count = int(df.duplicated().sum())

    columns: list[dict[str, Any]] = []
    total_missing_pct = 0.0

    for col_name in df.columns:
        series = df[col_name]
        detected_type = _detect_column_type(series)
        missing_count = int(series.isna().sum())
        missing_pct = (missing_count / row_count * 100) if row_count > 0 else 0.0

        total_missing_pct += missing_pct

        columns.append({
            "column_name": str(col_name),
            "detected_type": detected_type,
            "missing_count": missing_count,
            "missing_pct": round(missing_pct, 2),
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
    }
