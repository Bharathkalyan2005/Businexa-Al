"""Schema-agnostic column role detection using header hints + content inference."""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from app.services.analytics.business_types import BUSINESS_TYPE_CONFIGS

logger = logging.getLogger(__name__)

COLUMN_ROLES = (
    "date_column",
    "amount_column",
    "quantity_column",
    "cost_column",
    "category_column",
    "id_column",
    "status_column",
    "unassigned",
)

ROLE_PRIORITY = (
    "date_column",
    "amount_column",
    "cost_column",
    "category_column",
    "quantity_column",
    "id_column",
    "status_column",
)

ROLE_LABELS: dict[str, str] = {
    "date_column": "Date",
    "amount_column": "Revenue / Amount",
    "quantity_column": "Quantity",
    "cost_column": "Cost",
    "category_column": "Product / Category",
    "id_column": "Customer / ID",
    "status_column": "Status",
    "unassigned": "Unassigned",
}

# Header synonyms — hints only, not hardcoded primary detection.
ROLE_SYNONYMS: dict[str, list[str]] = {
    "date_column": [
        "date", "order date", "booking date", "transaction date", "sale date",
        "sold on", "timestamp", "created at", "purchased at", "invoice date",
        "period", "day", "datetime", "time", "order time", "booking time",
        "ship date", "delivery date", "posted date",
    ],
    "amount_column": [
        "revenue", "amount", "sales", "price", "total", "bill", "payment",
        "gross", "net", "sale total", "service fee", "gross sales",
        "total amount", "subtotal", "line total", "order value", "income",
        "charges", "fee", "paid", "sale amount", "transaction amount",
    ],
    "quantity_column": [
        "quantity", "qty", "units", "count", "pieces", "items sold",
        "unit count", "num units", "volume", "pack size",
    ],
    "cost_column": [
        "cost", "cogs", "expense", "unit cost", "cost price", "food cost",
        "ingredient cost", "purchase cost", "total cost", "overhead",
    ],
    "category_column": [
        "product", "item", "service", "category", "sku", "menu", "description",
        "product name", "item name", "service type", "menu item", "dish",
        "treatment", "job type", "line item", "product category",
    ],
    "id_column": [
        "customer", "client", "customer name", "client name", "buyer",
        "customer id", "client id", "customer email", "email", "account",
        "transaction id", "order id", "invoice id", "receipt number",
    ],
    "status_column": [
        "status", "order status", "payment status", "state", "fulfillment",
        "appt status", "appointment status", "refund status",
    ],
}

STATUS_VALUES = {
    "completed", "complete", "paid", "shipped", "delivered", "confirmed",
    "pending", "cancelled", "canceled", "refunded", "failed", "open",
    "closed", "in progress", "processing", "returned", "void",
}

DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y.%m.%d",
    "%m-%d-%Y",
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
)

CURRENCY_PATTERN = re.compile(r"^[\$€£¥₹]?\s*-?\s*[\d,]+\.?\d*$")
MIN_ROLE_SCORE = 0.35


def normalize_header(header: str) -> str:
    return re.sub(r"[_\-]+", " ", str(header).lower().strip())


def _fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _header_score(header: str, role: str, business_type: str) -> tuple[float, str]:
    normalized = normalize_header(header)
    tokens = set(normalized.split())
    best = 0.0
    best_match = ""

    candidates = list(ROLE_SYNONYMS.get(role, []))
    config = BUSINESS_TYPE_CONFIGS.get(business_type, BUSINESS_TYPE_CONFIGS["other"])
    semantic_map = {
        "date_column": "date",
        "amount_column": "revenue",
        "quantity_column": "quantity",
        "cost_column": "cost",
        "category_column": "product",
        "id_column": "customer",
        "status_column": "status",
    }
    semantic_key = semantic_map.get(role)
    if semantic_key and semantic_key in config.get("expected_columns", {}):
        candidates.extend(config["expected_columns"][semantic_key])

    for synonym in candidates:
        syn_norm = normalize_header(synonym)
        if syn_norm == normalized:
            return 1.0, f"exact header match '{synonym}'"
        if syn_norm in normalized or normalized in syn_norm:
            score = 0.92
            if score > best:
                best = score
                best_match = f"header contains '{synonym}'"
        syn_tokens = set(syn_norm.split())
        overlap = len(tokens & syn_tokens) / max(len(syn_tokens), 1)
        if overlap >= 0.5:
            score = 0.75 + overlap * 0.15
            if score > best:
                best = score
                best_match = f"header token overlap with '{synonym}'"
        fuzzy = _fuzzy_ratio(normalized, syn_norm)
        if fuzzy >= 0.78 and fuzzy > best:
            best = fuzzy * 0.85
            best_match = f"fuzzy header match '{synonym}' ({fuzzy:.0%})"

    return best, best_match or "no header hint"


def _parse_dates_rowwise(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna().astype(str).str.strip()
    non_null = non_null[non_null != ""]
    if len(non_null) == 0:
        return {"parse_rate": 0.0, "unparseable_rows": 0, "method": "empty"}

    parsed_count = 0
    for value in non_null.head(200):
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.notna(parsed):
            parsed_count += 1
            continue
        matched = False
        for fmt in DATE_FORMATS:
            try:
                pd.to_datetime(value, format=fmt)
                parsed_count += 1
                matched = True
                break
            except (ValueError, TypeError):
                continue
        if not matched:
            pass

    sample_len = min(len(non_null), 200)
    parse_rate = parsed_count / sample_len if sample_len else 0.0
    unparseable = int(sample_len - parsed_count)
    return {
        "parse_rate": round(parse_rate, 3),
        "unparseable_rows": unparseable,
        "method": "multi-format row-by-row",
    }


def _numeric_coercion_stats(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna()
    if len(non_null) == 0:
        return {"coercible_rate": 0.0, "has_currency_symbols": False, "median": None}

    def coerce(value: Any) -> bool:
        if pd.isna(value):
            return False
        s = str(value).strip()
        s = re.sub(r"[\$€£¥₹,\s]", "", s)
        try:
            float(s)
            return True
        except ValueError:
            return False

    sample = non_null.head(200)
    coercible = sample.apply(coerce).sum()
    has_currency = sample.astype(str).str.contains(r"[\$€£¥₹]", regex=True).any()
    numeric = pd.to_numeric(
        sample.astype(str).str.replace(r"[\$€£¥₹,\s]", "", regex=True),
        errors="coerce",
    )
    median = float(numeric.median()) if numeric.notna().any() else None
    return {
        "coercible_rate": round(coercible / len(sample), 3) if len(sample) else 0.0,
        "has_currency_symbols": bool(has_currency),
        "median": median,
    }


def _content_score(series: pd.Series, role: str, row_count: int) -> tuple[float, dict[str, Any]]:
    meta: dict[str, Any] = {}
    non_null = series.dropna()
    nunique = series.nunique()
    unique_ratio = nunique / max(len(non_null), 1)

    if role == "date_column":
        if pd.api.types.is_datetime64_any_dtype(series):
            return 0.95, {"reason": "native datetime dtype"}
        stats = _parse_dates_rowwise(series)
        meta.update(stats)
        score = stats["parse_rate"] * 0.95
        return score, meta

    if role in {"amount_column", "cost_column", "quantity_column"}:
        if pd.api.types.is_numeric_dtype(series):
            vals = pd.to_numeric(series, errors="coerce").dropna()
            if len(vals) == 0:
                return 0.0, {"reason": "numeric dtype but all null"}
            meta["median"] = float(vals.median())
            meta["is_integer_like"] = bool((vals % 1 == 0).mean() > 0.85)
            if role == "quantity_column":
                score = 0.55
                # Strong quantity signal: small integers with no currency context
                if meta["is_integer_like"] and meta["median"] <= 50:
                    score = 0.85
                elif meta["is_integer_like"] and meta["median"] <= 500:
                    score = 0.75
                if meta["median"] > 1000:
                    score -= 0.30
                return max(score, 0.0), meta
            score = 0.7
            if meta["median"] >= 1:
                score = 0.78
            # Large-value numerics are much more likely amount than quantity
            if meta["median"] > 100:
                score = min(score + 0.10, 0.95)
            if role == "cost_column":
                score *= 0.95
            return score, meta

        stats = _numeric_coercion_stats(series)
        meta.update(stats)
        if stats["coercible_rate"] < 0.5:
            return stats["coercible_rate"] * 0.4, meta
        score = stats["coercible_rate"] * 0.75
        median = stats.get("median")
        if role == "quantity_column":
            # Currency symbols are a strong signal AGAINST quantity
            if stats["has_currency_symbols"]:
                score -= 0.20
            if median is not None and median <= 50:
                score += 0.08
            elif median is not None and median > 1000:
                score -= 0.25
        elif role in {"amount_column", "cost_column"}:
            if stats["has_currency_symbols"]:
                score += 0.18  # Strong positive signal for amount/cost
            if median is not None and median >= 1:
                score += 0.08
        return min(score, 0.98), meta

    if role == "category_column":
        if pd.api.types.is_numeric_dtype(series):
            return 0.05, {"reason": "numeric column unlikely category"}
        if nunique <= 1:
            return 0.1, {"reason": "single unique value"}
        if unique_ratio < 0.5 or nunique <= max(50, row_count * 0.5):
            score = 0.65 + (0.25 if nunique <= 50 else 0.1)
            meta["unique_count"] = int(nunique)
            return min(score, 0.95), meta
        return 0.25, {"unique_count": int(nunique), "unique_ratio": round(unique_ratio, 3)}

    if role == "id_column":
        if pd.api.types.is_numeric_dtype(series) and nunique == len(non_null):
            return 0.55, {"unique_count": int(nunique)}
        if not pd.api.types.is_numeric_dtype(series):
            if unique_ratio > 0.5 or nunique >= max(5, row_count * 0.3):
                return 0.7, {"unique_count": int(nunique), "unique_ratio": round(unique_ratio, 3)}
        return 0.3, {"unique_count": int(nunique)}

    if role == "status_column":
        if pd.api.types.is_numeric_dtype(series):
            return 0.05, {"reason": "numeric unlikely status"}
        values = non_null.astype(str).str.strip().str.lower()
        if nunique > 15:
            return 0.15, {"unique_count": int(nunique)}
        status_hits = values.isin(STATUS_VALUES).mean()
        meta["status_value_match_rate"] = round(float(status_hits), 3)
        meta["unique_count"] = int(nunique)
        score = 0.4 + status_hits * 0.5 + (0.1 if nunique <= 8 else 0)
        return min(score, 0.95), meta

    return 0.0, {}


def score_column_for_roles(
    column_name: str,
    series: pd.Series,
    business_type: str,
    row_count: int,
) -> dict[str, Any]:
    """Score one column against all roles."""
    role_scores: dict[str, float] = {}
    role_details: dict[str, dict[str, Any]] = {}

    for role in COLUMN_ROLES:
        if role == "unassigned":
            continue
        header_s, header_reason = _header_score(column_name, role, business_type)
        content_s, content_meta = _content_score(series, role, row_count)
        combined = header_s * 0.45 + content_s * 0.55
        if header_s >= 0.9 and content_s >= 0.5:
            combined = min(0.99, combined + 0.08)
        role_scores[role] = round(combined, 3)
        role_details[role] = {
            "header_score": round(header_s, 3),
            "content_score": round(content_s, 3),
            "header_reason": header_reason,
            "content_meta": content_meta,
        }

    best_role = max(role_scores, key=role_scores.get)
    best_score = role_scores[best_role]
    if best_score < MIN_ROLE_SCORE:
        best_role = "unassigned"
        best_score = role_scores.get("unassigned", 0.0)

    return {
        "column_name": column_name,
        "detected_role": best_role,
        "role_confidence": round(best_score, 3),
        "role_scores": role_scores,
        "role_details": role_details,
        "reason": _build_reason(best_role, role_details.get(best_role, {})),
    }


def _build_reason(role: str, details: dict[str, Any]) -> str:
    if role == "unassigned":
        return "No strong role signal from header or content"
    header_reason = details.get("header_reason", "")
    content_meta = details.get("content_meta", {})
    parts = [header_reason] if header_reason else []
    if "parse_rate" in content_meta:
        parts.append(f"{content_meta['parse_rate']:.0%} of values parse as dates")
    if "coercible_rate" in content_meta:
        parts.append(f"{content_meta['coercible_rate']:.0%} coercible to numeric")
    if "unique_count" in content_meta:
        parts.append(f"{content_meta['unique_count']} unique values")
    return "; ".join(parts) if parts else f"inferred as {ROLE_LABELS.get(role, role)}"


def build_role_mapping(column_analyses: list[dict[str, Any]]) -> dict[str, str | None]:
    """Pick the best column for each role without reusing columns.

    Uses a two-pass algorithm:
    - Pass 1: assign columns whose ``detected_role`` exactly matches the target
      role (i.e. the column *wants* this role as its best overall fit). This
      prevents a higher-priority role from stealing a column that is clearly
      better suited for a lower-priority role.
    - Pass 2: for any role still unmapped, fill in with the best-scoring
      unused column (the original greedy approach, as a fallback).
    """
    mapping: dict[str, str | None] = {role: None for role in ROLE_PRIORITY}
    used: set[str] = set()

    # --- Pass 1: exact detected_role → role matches, ordered by score descending ---
    # Build a list of (role, column, score) for exact-match assignments
    exact_assignments: list[tuple[float, str, str]] = []
    for analysis in column_analyses:
        col = analysis["column_name"]
        detected = analysis.get("detected_role", "unassigned")
        if detected in mapping:
            score = analysis.get("role_confidence", 0.0)
            exact_assignments.append((score, col, detected))

    # Sort by score descending so higher-confidence assignments win ties
    exact_assignments.sort(key=lambda x: x[0], reverse=True)
    for score, col, role in exact_assignments:
        if col not in used and mapping[role] is None:
            mapping[role] = col
            used.add(col)

    # --- Pass 2: fill remaining unmapped roles greedily ---
    for role in ROLE_PRIORITY:
        if mapping[role] is not None:
            continue
        best_col: str | None = None
        best_score = MIN_ROLE_SCORE
        for analysis in column_analyses:
            col = analysis["column_name"]
            if col in used:
                continue
            score = analysis["role_scores"].get(role, 0.0)
            if score > best_score:
                best_score = score
                best_col = col
        if best_col:
            mapping[role] = best_col
            used.add(best_col)

    return mapping



def check_dashboard_viability(role_mapping: dict[str, str | None]) -> tuple[bool, str | None]:
    has_date = bool(role_mapping.get("date_column"))
    has_amount = bool(role_mapping.get("amount_column"))
    if not has_date and not has_amount:
        return False, (
            "We couldn't find a date column or a sales/amount column in this file — "
            "please check your file has at least these two."
        )
    if not has_date:
        return False, (
            "We couldn't find a date column in this file. "
            "Add a column with dates (e.g. order date, sale date) to see trends over time."
        )
    if not has_amount:
        return False, (
            "We couldn't find a sales/amount column in this file. "
            "Add a column with revenue or sale amounts to see financial KPIs."
        )
    return True, None


def detect_column_roles(
    df: pd.DataFrame,
    business_type: str,
) -> dict[str, Any]:
    """Detect roles for all columns and build a suggested mapping."""
    row_count = len(df)
    pipeline_log: list[dict[str, str]] = []
    column_analyses: list[dict[str, Any]] = []
    excluded_columns: list[dict[str, str]] = []

    for col_name in df.columns:
        series = df[col_name]
        non_null = series.dropna()
        if len(non_null) == 0:
            excluded_columns.append({
                "column": str(col_name),
                "reason": "Column is entirely empty — excluded from analysis",
            })
            pipeline_log.append({
                "level": "info",
                "message": f"Excluded empty column '{col_name}'",
            })
            column_analyses.append({
                "column_name": str(col_name),
                "detected_role": "unassigned",
                "role_confidence": 0.0,
                "role_scores": {},
                "role_details": {},
                "reason": "empty column",
                "excluded": True,
            })
            continue

        if not pd.api.types.is_numeric_dtype(series):
            stats = _numeric_coercion_stats(series)
            # Broaden: exclude any non-numeric column that can't be coerced AND
            # shows no meaningful role signal (not just single-value columns).
            if stats["coercible_rate"] < 0.1:
                # Quick pre-check: run header scores to see if any role wants it
                header_signals = [
                    _header_score(str(col_name), r, "other")[0]
                    for r in COLUMN_ROLES if r != "unassigned"
                ]
                max_header_signal = max(header_signals, default=0.0)
                if max_header_signal < MIN_ROLE_SCORE:
                    excluded_columns.append({
                        "column": str(col_name),
                        "reason": "Column has no usable numeric or date values and no recognisable header — excluded from analysis",
                    })
                    pipeline_log.append({
                        "level": "info",
                        "message": f"Excluded junk column '{col_name}' (non-numeric, coercible_rate={stats['coercible_rate']:.0%}, no header signal)",
                    })

        analysis = score_column_for_roles(str(col_name), series, business_type, row_count)
        column_analyses.append(analysis)
        pipeline_log.append({
            "level": "info",
            "message": (
                f"Column '{col_name}' → {analysis['detected_role']} "
                f"(confidence {analysis['role_confidence']:.0%}): {analysis['reason']}"
            ),
        })

    role_mapping = build_role_mapping(column_analyses)
    viable, error = check_dashboard_viability(role_mapping)

    for role, col in role_mapping.items():
        if col:
            pipeline_log.append({
                "level": "info",
                "message": f"Role mapping: {role} → '{col}'",
            })

    if not viable and error:
        pipeline_log.append({"level": "warning", "message": error})

    return {
        "columns": column_analyses,
        "role_mapping": role_mapping,
        "dashboard_viable": viable,
        "dashboard_error": error,
        "excluded_columns": excluded_columns,
        "pipeline_log": pipeline_log,
    }


def merge_role_mapping(
    auto_mapping: dict[str, str | None],
    user_mapping: dict[str, str | None] | None,
) -> dict[str, str | None]:
    """User overrides take precedence; empty string clears a role."""
    merged = dict(auto_mapping)
    if not user_mapping:
        return merged
    for role, col in user_mapping.items():
        if role not in ROLE_PRIORITY:
            continue
        merged[role] = col if col else None
    return merged


def suggest_ui_confirmations(
    role_mapping: dict[str, str | None],
    column_analyses: list[dict[str, Any]],
    confidence_threshold: float = 0.90,
) -> list[dict[str, Any]]:
    """Return user-facing confirmation prompts for low-confidence or ambiguous role assignments.

    Each item has:
      role         — the detected role key (e.g. 'amount_column')
      column       — the mapped column name
      confidence   — detection confidence (0–1)
      message      — human-readable confirmation question for the UI
    """
    confirmations: list[dict[str, Any]] = []
    role_by_column: dict[str, dict[str, Any]] = {
        a["column_name"]: a for a in column_analyses
    }

    for role, col in role_mapping.items():
        if col is None:
            continue
        analysis = role_by_column.get(col, {})
        confidence = analysis.get("role_confidence", 0.0)
        label = ROLE_LABELS.get(role, role)

        # Check whether another column came close (within 0.15 of best)
        best_score = analysis.get("role_scores", {}).get(role, 0.0)
        close_competitors = [
            a["column_name"]
            for a in column_analyses
            if a["column_name"] != col
            and abs(a.get("role_scores", {}).get(role, 0.0) - best_score) <= 0.15
            and a.get("role_scores", {}).get(role, 0.0) >= MIN_ROLE_SCORE
        ]

        if confidence < confidence_threshold or close_competitors:
            pct = int(round(confidence * 100))
            msg = (
                f"We detected \u2018{col}\u2019 as your {label} column "
                f"({pct}% confidence) \u2014 is that right?"
            )
            if close_competitors:
                alts = ", ".join(f"\u2018{c}\u2019" for c in close_competitors[:2])
                msg += f" (Alternatives: {alts})"
            confirmations.append({
                "role": role,
                "column": col,
                "confidence": round(confidence, 3),
                "message": msg,
            })
            logger.info(
                "UI confirmation suggested: role=%s col='%s' confidence=%.0f%%",
                role, col, confidence * 100,
            )

    return confirmations
