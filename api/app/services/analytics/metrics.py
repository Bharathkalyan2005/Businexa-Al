"""Core metric calculations — all deterministic, no LLM."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from app.services.analytics.business_types import resolve_column

logger = logging.getLogger(__name__)


def compute_metrics(
    df: pd.DataFrame,
    business_type: str,
) -> dict[str, Any]:
    """Compute all available KPIs from a cleaned DataFrame.

    Adapts which metrics are calculated based on which columns exist.
    Skips metrics when required columns are missing rather than guessing.

    Returns a dict ready for metrics_snapshots.raw_json.
    """
    cols = list(df.columns)
    metrics: dict[str, Any] = {
        "business_type": business_type,
        "row_count": len(df),
    }

    # --- Resolve columns ---
    date_col = resolve_column(cols, "date", business_type)
    revenue_col = resolve_column(cols, "revenue", business_type)
    product_col = resolve_column(cols, "product", business_type)
    quantity_col = resolve_column(cols, "quantity", business_type)
    cost_col = resolve_column(cols, "cost", business_type)
    customer_col = resolve_column(cols, "customer", business_type)
    profit_col = resolve_column(cols, "profit", business_type)

    metrics["resolved_columns"] = {
        "date": date_col,
        "revenue": revenue_col,
        "product": product_col,
        "quantity": quantity_col,
        "cost": cost_col,
        "customer": customer_col,
        "profit": profit_col,
    }

    # --- Parse dates if found ---
    if date_col and not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # --- Revenue metrics ---
    if revenue_col:
        rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
        total_revenue = float(rev_series.sum())
        metrics["revenue"] = round(total_revenue, 2)
        metrics["orders"] = int(len(df))
        metrics["average_order_value"] = round(
            total_revenue / len(df), 2
        ) if len(df) > 0 else 0.0

        # Revenue by period
        if date_col:
            df_sorted = df.copy()
            df_sorted["_revenue_num"] = rev_series
            df_sorted = df_sorted.dropna(subset=[date_col])

            if len(df_sorted) > 0:
                # Daily revenue
                daily = (
                    df_sorted.groupby(df_sorted[date_col].dt.date)["_revenue_num"]
                    .sum()
                    .reset_index()
                )
                daily.columns = ["date", "revenue"]
                daily["date"] = daily["date"].astype(str)
                metrics["revenue_by_day"] = daily.to_dict(orient="records")

                # Monthly revenue
                df_sorted["_month"] = df_sorted[date_col].dt.to_period("M").astype(str)
                monthly = (
                    df_sorted.groupby("_month")["_revenue_num"]
                    .sum()
                    .reset_index()
                )
                monthly.columns = ["month", "revenue"]
                metrics["revenue_by_month"] = monthly.to_dict(orient="records")

                # Growth % (month-over-month if 2+ months)
                if len(monthly) >= 2:
                    sorted_monthly = monthly.sort_values("month")
                    prev = float(sorted_monthly.iloc[-2]["revenue"])
                    curr = float(sorted_monthly.iloc[-1]["revenue"])
                    if prev > 0:
                        growth = round((curr - prev) / prev * 100, 2)
                        metrics["growth_pct"] = growth
                    else:
                        metrics["growth_pct"] = None
                else:
                    metrics["growth_pct"] = None
            else:
                metrics["growth_pct"] = None
    else:
        metrics["revenue"] = None
        metrics["orders"] = int(len(df))
        metrics["growth_pct"] = None

    # --- Product metrics ---
    if product_col and revenue_col:
        rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
        product_revenue = (
            df.assign(_rev=rev_series)
            .groupby(product_col)["_rev"]
            .sum()
            .sort_values(ascending=False)
        )

        total = float(product_revenue.sum())
        top_products = []
        for name, rev in product_revenue.head(3).items():
            top_products.append({
                "product": str(name),
                "revenue": round(float(rev), 2),
                "pct_of_total": round(float(rev) / total * 100, 2) if total > 0 else 0.0,
            })
        metrics["top_products"] = top_products
        metrics["top_product"] = top_products[0]["product"] if top_products else None

        bottom_products = []
        for name, rev in product_revenue.tail(3).items():
            bottom_products.append({
                "product": str(name),
                "revenue": round(float(rev), 2),
                "pct_of_total": round(float(rev) / total * 100, 2) if total > 0 else 0.0,
            })
        metrics["bottom_products"] = bottom_products
    else:
        metrics["top_products"] = []
        metrics["bottom_products"] = []
        metrics["top_product"] = None

    # --- Profit metrics ---
    if profit_col:
        profit_series = pd.to_numeric(df[profit_col], errors="coerce")
        total_profit = float(profit_series.sum())
        metrics["profit"] = round(total_profit, 2)
        if metrics.get("revenue") and metrics["revenue"] > 0:
            metrics["profit_margin"] = round(total_profit / metrics["revenue"] * 100, 2)
        else:
            metrics["profit_margin"] = None
    elif cost_col and revenue_col:
        # Calculate profit = revenue - cost
        rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
        cost_series = pd.to_numeric(df[cost_col], errors="coerce")
        profit_series = rev_series - cost_series
        total_profit = float(profit_series.sum())
        metrics["profit"] = round(total_profit, 2)
        if metrics.get("revenue") and metrics["revenue"] > 0:
            metrics["profit_margin"] = round(total_profit / metrics["revenue"] * 100, 2)
        else:
            metrics["profit_margin"] = None

        # Profit trend by day
        if date_col:
            df_profit = df.copy()
            df_profit["_profit"] = profit_series
            df_profit = df_profit.dropna(subset=[date_col])
            if len(df_profit) > 0:
                daily_profit = (
                    df_profit.groupby(df_profit[date_col].dt.date)["_profit"]
                    .sum()
                    .reset_index()
                )
                daily_profit.columns = ["date", "profit"]
                daily_profit["date"] = daily_profit["date"].astype(str)
                metrics["profit_by_day"] = daily_profit.to_dict(orient="records")
    else:
        metrics["profit"] = None
        metrics["profit_margin"] = None

    # --- Customer metrics ---
    if customer_col:
        unique_customers = df[customer_col].nunique()
        total_transactions = len(df)
        metrics["customer_count"] = int(unique_customers)

        # Repeat customer rate
        customer_counts = df[customer_col].value_counts()
        repeat_customers = int((customer_counts > 1).sum())
        metrics["repeat_customer_count"] = repeat_customers
        metrics["repeat_customer_rate"] = round(
            repeat_customers / unique_customers * 100, 2
        ) if unique_customers > 0 else 0.0
    else:
        metrics["customer_count"] = None
        metrics["repeat_customer_rate"] = None

    return metrics
