"""Core metric calculations — role-based, with graceful degradation."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.services.column_roles import (
    ROLE_LABELS,
    check_dashboard_viability,
    detect_column_roles,
    merge_role_mapping,
)

logger = logging.getLogger(__name__)

SKIPPED_METRIC_MESSAGES: dict[str, str] = {
    "revenue": "Add an amount/revenue column to see total revenue.",
    "orders": "Add transaction rows to see order counts.",
    "average_order_value": "Requires a revenue/amount column.",
    "growth_pct": "Requires a date column and at least two time periods of revenue data.",
    "revenue_trend": "Add a date column to see revenue trends over time.",
    "profit": "Add a Cost column or a Profit column to see net profit.",
    "profit_margin": "Add a Cost column to see profit margin.",
    "profit_trend": "Add a Cost or Profit column and a date column to see profit trends.",
    "top_products": "Add a product/category column and a revenue column to see top products.",
    "customer_count": "Add a customer or ID column to see customer metrics.",
    "repeat_customer_rate": "Add a customer or ID column with repeat transactions.",
}


def _log_skip(
    skipped: list[dict[str, str]],
    pipeline_log: list[dict[str, str]],
    metric: str,
    reason: str,
) -> None:
    skipped.append({"metric": metric, "reason": reason})
    pipeline_log.append({"level": "info", "message": f"Skipped metric '{metric}': {reason}"})
    logger.info("Skipped metric '%s': %s", metric, reason)


def compute_metrics(
    df: pd.DataFrame,
    business_type: str,
    role_mapping: dict[str, str | None] | None = None,
    auto_role_mapping: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Compute KPIs using column roles with graceful degradation.

    If neither ``role_mapping`` nor ``auto_role_mapping`` is supplied, column
    roles are auto-detected from the DataFrame so callers don't need to run
    profiling separately.
    """
    # Auto-detect roles when the caller provides no mapping at all
    if auto_role_mapping is None and role_mapping is None:
        detected = detect_column_roles(df, business_type)
        auto_role_mapping = detected["role_mapping"]
        logger.info(
            "compute_metrics: auto-detected role mapping for business_type=%s: %s",
            business_type,
            auto_role_mapping,
        )

    mapping = merge_role_mapping(auto_role_mapping or {}, role_mapping)
    viable, dashboard_error = check_dashboard_viability(mapping)

    skipped_metrics: list[dict[str, str]] = []
    pipeline_log: list[dict[str, str]] = [
        {"level": "info", "message": f"Analysis started for business_type={business_type}"},
        {"level": "info", "message": f"Using role mapping: {mapping}"},
    ]

    metrics: dict[str, Any] = {
        "business_type": business_type,
        "row_count": len(df),
        "role_mapping": mapping,
        "resolved_columns": {
            "date": mapping.get("date_column"),
            "revenue": mapping.get("amount_column"),
            "product": mapping.get("category_column"),
            "quantity": mapping.get("quantity_column"),
            "cost": mapping.get("cost_column"),
            "customer": mapping.get("id_column"),
            "status": mapping.get("status_column"),
            "profit": None,
        },
        "dashboard_viable": viable,
        "dashboard_error": dashboard_error,
        "skipped_metrics": skipped_metrics,
        "pipeline_log": pipeline_log,
        "available_sections": [],
    }

    if not viable:
        pipeline_log.append({"level": "error", "message": dashboard_error or "Dashboard not viable"})
        return metrics

    date_col = mapping.get("date_column")
    revenue_col = mapping.get("amount_column")
    product_col = mapping.get("category_column")
    quantity_col = mapping.get("quantity_column")
    cost_col = mapping.get("cost_column")
    customer_col = mapping.get("id_column")

    if date_col and date_col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # --- Revenue ---
    if revenue_col and revenue_col in df.columns:
        rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
        total_revenue = float(rev_series.sum())
        metrics["revenue"] = round(total_revenue, 2)
        metrics["orders"] = int(len(df))
        metrics["average_order_value"] = round(total_revenue / len(df), 2) if len(df) > 0 else 0.0
        metrics["available_sections"].append("revenue")

        if date_col and date_col in df.columns:
            df_sorted = df.dropna(subset=[date_col]).copy()
            df_sorted["_revenue_num"] = rev_series.loc[df_sorted.index]

            if len(df_sorted) > 0:
                daily = (
                    df_sorted.groupby(df_sorted[date_col].dt.date)["_revenue_num"]
                    .sum()
                    .reset_index()
                )
                daily.columns = ["date", "revenue"]
                daily["date"] = daily["date"].astype(str)
                metrics["revenue_by_day"] = daily.to_dict(orient="records")

                df_sorted["_month"] = df_sorted[date_col].dt.to_period("M").astype(str)
                monthly = df_sorted.groupby("_month")["_revenue_num"].sum().reset_index()
                monthly.columns = ["month", "revenue"]
                metrics["revenue_by_month"] = monthly.to_dict(orient="records")
                metrics["available_sections"].append("revenue_trend")

                if len(monthly) >= 2:
                    sorted_monthly = monthly.sort_values("month")
                    prev = float(sorted_monthly.iloc[-2]["revenue"])
                    curr = float(sorted_monthly.iloc[-1]["revenue"])
                    metrics["growth_pct"] = round((curr - prev) / prev * 100, 2) if prev > 0 else None
                else:
                    metrics["growth_pct"] = None
                    _log_skip(
                        skipped_metrics,
                        pipeline_log,
                        "growth_pct",
                        SKIPPED_METRIC_MESSAGES["growth_pct"],
                    )
            else:
                metrics["growth_pct"] = None
                _log_skip(skipped_metrics, pipeline_log, "revenue_trend", "No parseable dates for trend chart.")
        else:
            metrics["growth_pct"] = None
            _log_skip(skipped_metrics, pipeline_log, "revenue_trend", SKIPPED_METRIC_MESSAGES["revenue_trend"])
            _log_skip(skipped_metrics, pipeline_log, "growth_pct", SKIPPED_METRIC_MESSAGES["growth_pct"])
    else:
        metrics["revenue"] = None
        metrics["orders"] = int(len(df))
        metrics["average_order_value"] = None
        metrics["growth_pct"] = None
        for key in ("revenue", "average_order_value", "growth_pct", "revenue_trend"):
            _log_skip(skipped_metrics, pipeline_log, key, SKIPPED_METRIC_MESSAGES[key])

    # --- Products ---
    if product_col and product_col in df.columns and revenue_col and revenue_col in df.columns:
        rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
        product_revenue = (
            df.assign(_rev=rev_series)
            .groupby(product_col)["_rev"]
            .sum()
            .sort_values(ascending=False)
        )
        total = float(product_revenue.sum())
        top_products = [
            {
                "product": str(name),
                "revenue": round(float(rev), 2),
                "pct_of_total": round(float(rev) / total * 100, 2) if total > 0 else 0.0,
            }
            for name, rev in product_revenue.head(3).items()
        ]
        bottom_products = [
            {
                "product": str(name),
                "revenue": round(float(rev), 2),
                "pct_of_total": round(float(rev) / total * 100, 2) if total > 0 else 0.0,
            }
            for name, rev in product_revenue.tail(3).items()
        ]
        metrics["top_products"] = top_products
        metrics["bottom_products"] = bottom_products
        metrics["top_product"] = top_products[0]["product"] if top_products else None
        metrics["available_sections"].append("top_products")
    else:
        metrics["top_products"] = []
        metrics["bottom_products"] = []
        metrics["top_product"] = None
        _log_skip(skipped_metrics, pipeline_log, "top_products", SKIPPED_METRIC_MESSAGES["top_products"])

    # --- Profit ---
    profit_col = None
    if cost_col and cost_col in df.columns and revenue_col and revenue_col in df.columns:
        rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
        cost_series = pd.to_numeric(df[cost_col], errors="coerce")
        profit_series = rev_series - cost_series
        total_profit = float(profit_series.sum())
        metrics["profit"] = round(total_profit, 2)
        if metrics.get("revenue") and metrics["revenue"] > 0:
            metrics["profit_margin"] = round(total_profit / metrics["revenue"] * 100, 2)
        else:
            metrics["profit_margin"] = None
        metrics["available_sections"].append("profit")

        if date_col and date_col in df.columns:
            df_profit = df.dropna(subset=[date_col]).copy()
            df_profit["_profit"] = profit_series.loc[df_profit.index]
            if len(df_profit) > 0:
                daily_profit = (
                    df_profit.groupby(df_profit[date_col].dt.date)["_profit"]
                    .sum()
                    .reset_index()
                )
                daily_profit.columns = ["date", "profit"]
                daily_profit["date"] = daily_profit["date"].astype(str)
                metrics["profit_by_day"] = daily_profit.to_dict(orient="records")
                metrics["available_sections"].append("profit_trend")
            else:
                _log_skip(skipped_metrics, pipeline_log, "profit_trend", SKIPPED_METRIC_MESSAGES["profit_trend"])
    else:
        metrics["profit"] = None
        metrics["profit_margin"] = None
        _log_skip(skipped_metrics, pipeline_log, "profit", SKIPPED_METRIC_MESSAGES["profit"])
        _log_skip(skipped_metrics, pipeline_log, "profit_margin", SKIPPED_METRIC_MESSAGES["profit_margin"])
        _log_skip(skipped_metrics, pipeline_log, "profit_trend", SKIPPED_METRIC_MESSAGES["profit_trend"])

    if quantity_col and quantity_col in df.columns:
        qty_series = pd.to_numeric(df[quantity_col], errors="coerce")
        metrics["total_quantity"] = round(float(qty_series.sum()), 2)
        metrics["available_sections"].append("quantity")

    # --- Customers ---
    if customer_col and customer_col in df.columns:
        unique_customers = df[customer_col].nunique()
        metrics["customer_count"] = int(unique_customers)
        customer_counts = df[customer_col].value_counts()
        repeat_customers = int((customer_counts > 1).sum())
        metrics["repeat_customer_count"] = repeat_customers
        metrics["repeat_customer_rate"] = round(
            repeat_customers / unique_customers * 100, 2
        ) if unique_customers > 0 else 0.0
        metrics["available_sections"].append("customers")
    else:
        metrics["customer_count"] = None
        metrics["repeat_customer_rate"] = None
        _log_skip(skipped_metrics, pipeline_log, "customer_count", SKIPPED_METRIC_MESSAGES["customer_count"])
        _log_skip(
            skipped_metrics,
            pipeline_log,
            "repeat_customer_rate",
            SKIPPED_METRIC_MESSAGES["repeat_customer_rate"],
        )

    pipeline_log.append({
        "level": "info",
        "message": f"Computed sections: {', '.join(metrics['available_sections']) or 'none'}",
    })

    return metrics
