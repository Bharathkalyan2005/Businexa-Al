"""Data cleaning service — dedup, missing values, normalization."""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _strip_currency(value: Any) -> Any:
    """Remove currency symbols and commas from a string value."""
    if pd.isna(value):
        return value
    s = str(value).strip()
    s = re.sub(r"[\$€£¥₹,\s]", "", s)
    try:
        return float(s)
    except ValueError:
        return value


def clean_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Clean a DataFrame and return the cleaned data plus a summary."""
    original_row_count = len(df)
    summary: dict[str, Any] = {
        "original_row_count": original_row_count,
        "duplicates_removed": 0,
        "values_imputed": 0,
        "currency_columns_normalized": 0,
        "remaining_issues": [],
    }

    # 1. Remove exact duplicates
    before_dedup = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    summary["duplicates_removed"] = before_dedup - len(df)

    # 2. Impute missing values
    values_imputed = 0
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        if missing_count == 0:
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            median_val = df[col].median()
            if pd.notna(median_val):
                df[col] = df[col].fillna(median_val)
                values_imputed += missing_count
            else:
                summary["remaining_issues"].append(f"Column '{col}': all values missing.")
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            summary["remaining_issues"].append(f"Column '{col}': {missing_count} missing date(s).")
        else:
            df[col] = df[col].fillna("Unknown")
            values_imputed += missing_count

    summary["values_imputed"] = values_imputed

    # 3. Normalize currency columns
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            sample = df[col].dropna().astype(str).head(20)
            if len(sample) == 0:
                continue

            currency_pattern = re.compile(r"^[\$€£¥₹]?\s*-?\s*[\d,]+\.?\d*$")
            match_rate = sample.apply(lambda x: bool(currency_pattern.match(x.strip()))).sum() / len(sample)

            if match_rate >= 0.7:
                df[col] = df[col].apply(_strip_currency)
                df[col] = pd.to_numeric(df[col], errors="coerce")
                summary["currency_columns_normalized"] += 1

    summary["cleaned_row_count"] = len(df)

    return {
        "cleaned_df": df,
        "summary": summary,
    }
