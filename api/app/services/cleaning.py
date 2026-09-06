"""Data cleaning service — dedup, missing values, normalization with row-level logging."""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

from app.services.column_roles import DATE_FORMATS

logger = logging.getLogger(__name__)


def _strip_currency(value: Any) -> Any:
    if pd.isna(value):
        return value
    s = str(value).strip()
    s = re.sub(r"[\$€£¥₹,\s]", "", s)
    try:
        return float(s)
    except ValueError:
        return value


def _parse_date_value(value: Any) -> tuple[Any, bool]:
    if pd.isna(value):
        return pd.NaT, False
    if isinstance(value, pd.Timestamp):
        return value, True

    text = str(value).strip()
    if not text:
        return pd.NaT, False

    parsed = pd.to_datetime(text, errors="coerce")
    if pd.notna(parsed):
        return parsed, True

    for fmt in DATE_FORMATS:
        try:
            return pd.to_datetime(text, format=fmt), True
        except (ValueError, TypeError):
            continue

    return pd.NaT, False


def clean_dataframe(
    df: pd.DataFrame,
    role_mapping: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Clean a DataFrame and return the cleaned data plus a detailed summary."""
    original_row_count = len(df)
    summary: dict[str, Any] = {
        "original_row_count": original_row_count,
        "duplicates_removed": 0,
        "values_imputed": 0,
        "currency_columns_normalized": 0,
        "date_parse_failures": 0,
        "numeric_coercion_failures": 0,
        "excluded_columns": [],
        "remaining_issues": [],
        "pipeline_log": [],
    }

    df = df.copy()

    # Drop entirely empty columns
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    for col in empty_cols:
        summary["excluded_columns"].append(str(col))
        summary["pipeline_log"].append({
            "level": "info",
            "message": f"Excluded empty column '{col}' during cleaning",
        })
    if empty_cols:
        df = df.drop(columns=empty_cols)

    before_dedup = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    summary["duplicates_removed"] = before_dedup - len(df)

    date_col = role_mapping.get("date_column") if role_mapping else None
    amount_col = role_mapping.get("amount_column") if role_mapping else None
    cost_col = role_mapping.get("cost_column") if role_mapping else None
    qty_col = role_mapping.get("quantity_column") if role_mapping else None
    numeric_roles = {c for c in [amount_col, cost_col, qty_col] if c}

    # Row-by-row date parsing for mapped date column
    if date_col and date_col in df.columns:
        parsed_values = []
        failures = 0
        for value in df[date_col]:
            parsed, ok = _parse_date_value(value)
            parsed_values.append(parsed)
            if not ok and pd.notna(value) and str(value).strip():
                failures += 1
        df[date_col] = parsed_values
        summary["date_parse_failures"] = failures
        if failures:
            summary["remaining_issues"].append(
                f"Column '{date_col}': {failures} row(s) could not be parsed as dates."
            )
            summary["pipeline_log"].append({
                "level": "warning",
                "message": f"Flagged {failures} unparseable date values in '{date_col}'",
            })

    # Normalize numeric role columns
    currency_pattern = re.compile(r"^[\$€£¥₹]?\s*-?\s*[\d,]+\.?\d*$")
    for col in df.columns:
        if col in numeric_roles or (
            not pd.api.types.is_numeric_dtype(df[col])
            and df[col].dropna().astype(str).head(20).apply(
                lambda x: bool(currency_pattern.match(str(x).strip()))
            ).mean() >= 0.5
        ):
            original = df[col].copy()
            coerced = df[col].apply(_strip_currency)
            coerced = pd.to_numeric(coerced, errors="coerce")
            failures = int((original.notna() & coerced.isna()).sum())
            summary["numeric_coercion_failures"] += failures
            df[col] = coerced
            if failures:
                summary["remaining_issues"].append(
                    f"Column '{col}': {failures} value(s) could not be converted to numbers."
                )
            if col in numeric_roles:
                summary["currency_columns_normalized"] += 1

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
            summary["remaining_issues"].append(
                f"Column '{col}': {missing_count} missing date(s) left as null."
            )
        else:
            df[col] = df[col].fillna("Unknown")
            values_imputed += missing_count

    summary["values_imputed"] = values_imputed
    summary["cleaned_row_count"] = len(df)

    return {
        "cleaned_df": df,
        "summary": summary,
    }
