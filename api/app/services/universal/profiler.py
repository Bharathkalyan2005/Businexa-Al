"""
Stage 1 — Universal Deterministic Data Profiler
================================================
Schema-agnostic profiling of ANY tabular DataFrame.
No LLM. No hardcoded domain assumptions.
Outputs a single structured JSON-serialisable dict ("DataProfile").

Public API
----------
    profile = build_data_profile(df, sample_rows=8)

Column-type taxonomy
--------------------
    numeric          — int or float columns (after stripping currency symbols)
    categorical      — low-to-medium cardinality string columns (<=50 uniques
                       OR unique_ratio < 0.3)
    datetime         — parseable date/time columns
    boolean          — binary columns (0/1, True/False, Yes/No, etc.)
    free_text        — high-cardinality string, likely prose
    id_like          — very-high-cardinality string/numeric (looks like IDs)
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_CURRENCY_RE = re.compile(r"[\$\u20ac\xa3\xa5\u20b9,]")
_BOOL_TRUE = frozenset({"1", "true", "yes", "y", "t", "on", "pass", "positive"})
_BOOL_FALSE = frozenset({"0", "false", "no", "n", "f", "off", "fail", "negative"})
_BOOL_ALL = _BOOL_TRUE | _BOOL_FALSE
_LABEL_LIKE_VALUES = frozenset({
    "yes", "no", "true", "false",
    "pass", "fail",
    "active", "inactive",
    "churned", "retained",
    "positive", "negative",
    "survived", "died",
    "approved", "rejected",
    "good", "bad",
    "high", "low",
    "1", "0",
})
_TARGET_MAX_UNIQUE = 10          # binary/low-cardinality label ceiling
_CATEGORICAL_MAX_UNIQUE = 50     # hard ceiling for categorical type
_CATEGORICAL_MAX_RATIO = 0.30    # unique/non-null ratio ceiling
_GROUPBY_MAX_UNIQUE = 15         # max uniques for group-by aggregates
_OUTLIER_IQR_FACTOR = 1.5
_DATE_PARSE_SAMPLE = 200
_DATE_SUCCESS_MIN = 0.60
_SAMPLE_ROWS = 8


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val: Any) -> float | None:
    """Convert to float, returning None on failure."""
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """Strip currency/comma formatting then coerce to float."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    # Replace NaN with empty string before regex sub to avoid TypeError
    cleaned = series.fillna("").astype(str).str.strip()
    cleaned = cleaned.str.replace(_CURRENCY_RE, "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def _is_datetime_series(series: pd.Series) -> bool:
    """Return True if >=60 % of non-null values parse as dates."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if pd.api.types.is_numeric_dtype(series):
        return False
    non_null = series.dropna().astype(str).str.strip()
    non_null = non_null[non_null != ""]
    if len(non_null) == 0:
        return False
    # Require at least one date separator character to avoid false positives
    sample = non_null.head(_DATE_PARSE_SAMPLE)
    has_sep = sample.str.contains(r"[-/. ,]", regex=True)
    if has_sep.mean() < 0.4:
        return False
    parsed = pd.to_datetime(sample, errors="coerce")
    return parsed.notna().mean() >= _DATE_SUCCESS_MIN


def _parse_datetime_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series, errors="coerce")


def _is_boolean_series(series: pd.Series, nunique: int) -> bool:
    """True if the column is effectively binary after normalisation."""
    if nunique > 2:
        return False
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    if pd.api.types.is_numeric_dtype(series):
        vals = set(pd.to_numeric(non_null, errors="coerce").dropna().unique())
        return vals <= {0.0, 1.0}
    vals = set(non_null.astype(str).str.strip().str.lower().unique())
    return vals <= _BOOL_ALL


def _looks_like_prose(series: pd.Series) -> bool:
    """Return True if non-null string values look like natural-language prose.

    Heuristic: average word count >= 4 for a sample of values.
    ID-like values (order codes, UUIDs, short labels) have few or no spaces.
    """
    sample = series.dropna().astype(str).head(50)
    if len(sample) == 0:
        return False
    avg_words = sample.str.split().apply(len).mean()
    return avg_words >= 4


def _classify_column(
    series: pd.Series,
    col: str,
    row_count: int,
) -> str:
    """Return one of: numeric | categorical | datetime | boolean | free_text | id_like."""
    non_null = series.dropna()
    n_non_null = len(non_null)
    nunique = series.nunique(dropna=True)

    # --- datetime check first (before numeric, epoch ints are not dates)
    if _is_datetime_series(series):
        return "datetime"

    # --- boolean check before numeric — a 0/1 int column is boolean, not numeric
    if _is_boolean_series(series, nunique):
        return "boolean"

    # --- numeric (native or coercible via currency stripping)
    numeric_coerced = _coerce_numeric(series)
    coerce_rate = numeric_coerced.notna().sum() / max(n_non_null, 1)
    if coerce_rate >= 0.85:
        coerced_non_null = numeric_coerced.dropna()
        is_integer_like = bool((coerced_non_null % 1 == 0).all())
        # Only treat as id_like if: all unique AND all integer-valued
        # (floats are measurements, never IDs)
        if is_integer_like and nunique == n_non_null and nunique > 50:
            return "id_like"
        return "numeric"

    if n_non_null == 0:
        return "categorical"

    # --- high-cardinality string check
    unique_ratio = nunique / n_non_null
    if unique_ratio > 0.85 and nunique >= 50:
        # Distinguish prose (free_text) from actual IDs
        if _looks_like_prose(series):
            return "free_text"
        return "id_like"

    # --- categorical vs free-text
    if nunique <= _CATEGORICAL_MAX_UNIQUE or unique_ratio <= _CATEGORICAL_MAX_RATIO:
        return "categorical"

    return "free_text"


def _null_pct(series: pd.Series, row_count: int) -> float:
    if row_count == 0:
        return 0.0
    return round(series.isna().sum() / row_count * 100, 2)


# ── Per-type stats ────────────────────────────────────────────────────────────

def _numeric_stats(series: pd.Series, col_type: str) -> dict[str, Any]:
    vals = _coerce_numeric(series).dropna()
    if len(vals) == 0:
        return {"error": "no_numeric_values"}

    q1 = float(vals.quantile(0.25))
    q3 = float(vals.quantile(0.75))
    iqr = q3 - q1
    fence_lo = q1 - _OUTLIER_IQR_FACTOR * iqr
    fence_hi = q3 + _OUTLIER_IQR_FACTOR * iqr
    outlier_count = int(((vals < fence_lo) | (vals > fence_hi)).sum())

    return {
        "min": _safe_float(vals.min()),
        "max": _safe_float(vals.max()),
        "mean": _safe_float(vals.mean()),
        "median": _safe_float(vals.median()),
        "std": _safe_float(vals.std()),
        "q1": _safe_float(q1),
        "q3": _safe_float(q3),
        "outlier_count": outlier_count,
        "non_null_count": len(vals),
    }


def _categorical_stats(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna().astype(str).str.strip()
    vc = non_null.value_counts()
    total = len(non_null)
    top5 = [
        {
            "value": v,
            "count": int(c),
            "pct": round(c / total * 100, 1) if total else 0.0,
        }
        for v, c in vc.head(5).items()
    ]
    return {
        "unique_count": int(series.nunique(dropna=True)),
        "top_values": top5,
        "non_null_count": total,
    }


def _datetime_stats(series: pd.Series) -> dict[str, Any]:
    parsed = _parse_datetime_series(series).dropna()
    if len(parsed) == 0:
        return {"error": "no_parseable_dates"}
    mn = parsed.min()
    mx = parsed.max()
    span_days = (mx - mn).days

    if span_days <= 31:
        granularity = "day"
    elif span_days <= 366:
        granularity = "month"
    elif span_days <= 366 * 3:
        granularity = "quarter"
    else:
        granularity = "year"

    return {
        "min": mn.isoformat(),
        "max": mx.isoformat(),
        "span_days": span_days,
        "granularity": granularity,
        "non_null_count": len(parsed),
    }


def _boolean_stats(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna()
    if pd.api.types.is_numeric_dtype(series):
        vals = pd.to_numeric(non_null, errors="coerce").dropna()
        true_count = int((vals == 1).sum())
    else:
        normed = non_null.astype(str).str.strip().str.lower()
        true_count = int(normed.isin(_BOOL_TRUE).sum())
    total = len(non_null)
    false_count = total - true_count
    return {
        "true_count": true_count,
        "false_count": false_count,
        "true_pct": round(true_count / total * 100, 1) if total else 0.0,
        "non_null_count": total,
    }


# ── Correlation matrix ────────────────────────────────────────────────────────

def _correlation_matrix(df: pd.DataFrame, numeric_cols: list[str]) -> dict[str, Any]:
    """Pearson correlation matrix across numeric columns."""
    if len(numeric_cols) < 2:
        return {}
    sub = pd.DataFrame({c: _coerce_numeric(df[c]) for c in numeric_cols})
    corr = sub.corr(method="pearson")
    result: dict[str, dict[str, float | None]] = {}
    for row_col in corr.index:
        result[str(row_col)] = {}
        for col_col in corr.columns:
            val = corr.loc[row_col, col_col]
            result[str(row_col)][str(col_col)] = _safe_float(val)
    return result


# ── Group-by aggregates ───────────────────────────────────────────────────────

def _groupby_aggregates(
    df: pd.DataFrame,
    categorical_cols: list[str],
    numeric_cols: list[str],
) -> dict[str, Any]:
    """
    For every categorical column with < _GROUPBY_MAX_UNIQUE unique values,
    compute mean and count for each numeric column.

    Returns:
        {
          "CategoryCol": {
            "NumericCol": [
              {"group": "A", "mean": 12.3, "count": 45},
              ...
            ],
          },
        }
    """
    aggregates: dict[str, Any] = {}
    for cat_col in categorical_cols:
        n_unique = df[cat_col].nunique(dropna=True)
        if n_unique > _GROUPBY_MAX_UNIQUE or n_unique < 2:
            continue
        agg_by_col: dict[str, list[dict[str, Any]]] = {}
        for num_col in numeric_cols:
            numeric_vals = _coerce_numeric(df[num_col])
            temp = pd.DataFrame(
                {cat_col: df[cat_col], num_col: numeric_vals}
            ).dropna()
            if temp.empty:
                continue
            grouped = (
                temp.groupby(cat_col)[num_col]
                .agg(["mean", "count"])
                .reset_index()
            )
            rows = []
            for _, row in grouped.iterrows():
                rows.append({
                    "group": str(row[cat_col]),
                    "mean": _safe_float(row["mean"]),
                    "count": int(row["count"]),
                })
            agg_by_col[num_col] = rows
        if agg_by_col:
            aggregates[cat_col] = agg_by_col
    return aggregates


# ── Target column detection ───────────────────────────────────────────────────

def _detect_target_column(
    df: pd.DataFrame,
    column_profiles: list[dict[str, Any]],
) -> str | None:
    """
    Heuristically find the most likely "label / outcome" column.

    Priority rules (highest score wins):
    1. Numeric binary (0/1) — clearest machine-learning target signal
    2. Boolean column (string Yes/No, True/False) — slightly lower than numeric binary
       because numeric binary is more commonly an explicit encoded label
    3. Categorical where all top values are in _LABEL_LIKE_VALUES, 2 uniques
    4. Categorical with label-like values, <= _TARGET_MAX_UNIQUE uniques
    5. 2-unique categorical (any values)
    """
    candidates: list[tuple[float, str]] = []

    for cp in column_profiles:
        col = cp["column"]
        col_type = cp["type"]
        stats = cp.get("stats", {})

        if col_type == "numeric":
            coerced = _coerce_numeric(df[col]).dropna()
            uniq = set(coerced.unique())
            if uniq <= {0.0, 1.0} and len(uniq) == 2:
                # Numeric 0/1 is the canonical ML target — highest priority
                candidates.append((0.97, col))
            continue

        if col_type == "boolean":
            # Prefer numeric-encoded boolean (0/1 int) over string boolean (Yes/No)
            # as the target/outcome column: numeric encoding is the ML convention
            is_numeric_encoded = pd.api.types.is_numeric_dtype(df[col])
            score = 0.93 if is_numeric_encoded else 0.87
            candidates.append((score, col))
            continue

        if col_type == "categorical":
            unique_count = stats.get("unique_count", 999)
            top_values = {
                tv["value"].lower() for tv in stats.get("top_values", [])
            }
            all_label_like = bool(top_values) and top_values <= _LABEL_LIKE_VALUES
            if all_label_like and unique_count <= 2:
                candidates.append((0.85, col))
            elif all_label_like and unique_count <= _TARGET_MAX_UNIQUE:
                candidates.append((0.75, col))
            elif unique_count == 2:
                candidates.append((0.60, col))
            elif unique_count <= _TARGET_MAX_UNIQUE:
                candidates.append((0.45, col))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


# ── Sample rows ───────────────────────────────────────────────────────────────

def _sample_rows(df: pd.DataFrame, n: int = _SAMPLE_ROWS) -> list[dict[str, Any]]:
    """Return n representative rows, serialised to JSON-safe types."""
    sample = df.head(n)
    rows = []
    for _, row in sample.iterrows():
        record: dict[str, Any] = {}
        for col, val in row.items():
            try:
                is_na = pd.isna(val)
            except (TypeError, ValueError):
                is_na = False
            if is_na:
                record[str(col)] = None
            elif isinstance(val, (np.integer,)):
                record[str(col)] = int(val)
            elif isinstance(val, (np.floating,)):
                f = float(val)
                record[str(col)] = None if math.isnan(f) else f
            elif isinstance(val, pd.Timestamp):
                record[str(col)] = val.isoformat()
            else:
                record[str(col)] = str(val)
        rows.append(record)
    return rows


# ── Main entry point ──────────────────────────────────────────────────────────

def build_data_profile(
    df: pd.DataFrame,
    sample_rows: int = _SAMPLE_ROWS,
) -> dict[str, Any]:
    """
    Build the full Stage 1 data profile for any DataFrame.

    Parameters
    ----------
    df          : The uploaded/parsed DataFrame (any schema).
    sample_rows : Number of representative rows to include in the profile.

    Returns
    -------
    A JSON-serialisable dict — the "DataProfile" object consumed by Stage 2.
    """
    if df.empty:
        return {
            "row_count": 0,
            "col_count": len(df.columns),
            "is_sparse": True,
            "columns": [],
            "correlation_matrix": {},
            "groupby_aggregates": {},
            "target_column": None,
            "sample_rows": [],
            "degraded_mode": True,
            "degraded_reason": "Dataset is empty — no rows to profile.",
            "numeric_columns": [],
            "categorical_columns": [],
            "datetime_columns": [],
            "boolean_columns": [],
            "id_like_columns": [],
            "free_text_columns": [],
        }

    row_count = len(df)
    col_count = len(df.columns)

    # --- classify every column
    column_profiles: list[dict[str, Any]] = []
    numeric_cols: list[str] = []
    categorical_cols: list[str] = []
    datetime_cols: list[str] = []
    boolean_cols: list[str] = []

    for col in df.columns:
        col_str = str(col)
        series = df[col]
        col_type = _classify_column(series, col_str, row_count)
        null_pct = _null_pct(series, row_count)

        profile: dict[str, Any] = {
            "column": col_str,
            "type": col_type,
            "null_pct": null_pct,
        }

        if col_type == "numeric":
            profile["stats"] = _numeric_stats(series, col_type)
            numeric_cols.append(col_str)
        elif col_type == "categorical":
            profile["stats"] = _categorical_stats(series)
            categorical_cols.append(col_str)
        elif col_type == "datetime":
            profile["stats"] = _datetime_stats(series)
            datetime_cols.append(col_str)
        elif col_type == "boolean":
            profile["stats"] = _boolean_stats(series)
            boolean_cols.append(col_str)
        elif col_type in ("free_text", "id_like"):
            profile["stats"] = {
                "unique_count": int(series.nunique(dropna=True)),
                "non_null_count": int(series.notna().sum()),
            }

        column_profiles.append(profile)

    # --- degraded mode: too few rows or no useful columns
    # id_like and free_text columns are NOT useful for dashboard visualisations
    has_useful_cols = bool(numeric_cols or categorical_cols or boolean_cols)
    degraded = False
    degraded_reason: str | None = None
    if row_count < 20:
        degraded = True
        degraded_reason = (
            f"Only {row_count} rows — dashboard will show a summary view."
        )
    elif not has_useful_cols:
        degraded = True
        degraded_reason = (
            "No numeric or categorical columns found — "
            "cannot generate full dashboard."
        )

    # --- cross-column analyses (only when not degraded)
    corr_matrix: dict[str, Any] = {}
    groupby_aggs: dict[str, Any] = {}
    target_col: str | None = None

    if not degraded:
        corr_matrix = _correlation_matrix(df, numeric_cols)
        groupby_aggs = _groupby_aggregates(df, categorical_cols, numeric_cols)
        target_col = _detect_target_column(df, column_profiles)

    return {
        "row_count": row_count,
        "col_count": col_count,
        "is_sparse": degraded,
        "degraded_mode": degraded,
        "degraded_reason": degraded_reason,
        "columns": column_profiles,
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
        "boolean_columns": boolean_cols,
        "id_like_columns": [
            cp["column"] for cp in column_profiles if cp["type"] == "id_like"
        ],
        "free_text_columns": [
            cp["column"] for cp in column_profiles if cp["type"] == "free_text"
        ],
        "correlation_matrix": corr_matrix,
        "groupby_aggregates": groupby_aggs,
        "target_column": target_col,
        "sample_rows": _sample_rows(df, sample_rows),
    }
