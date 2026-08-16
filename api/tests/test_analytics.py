"""Tests for deterministic analytics calculations."""

import pandas as pd
import pytest

from app.services.analytics.metrics import compute_metrics


def test_revenue_and_orders(clean_sales_df: pd.DataFrame):
    metrics = compute_metrics(clean_sales_df, "retail")
    assert metrics["revenue"] is not None
    assert metrics["revenue"] > 2000
    assert metrics["orders"] == 12
    assert metrics["average_order_value"] == round(metrics["revenue"] / 12, 2)


def test_top_products(clean_sales_df: pd.DataFrame):
    metrics = compute_metrics(clean_sales_df, "retail")
    assert len(metrics["top_products"]) <= 3
    assert metrics["top_product"] is not None
    assert metrics["top_products"][0]["pct_of_total"] > 0


def test_customer_metrics(clean_sales_df: pd.DataFrame):
    metrics = compute_metrics(clean_sales_df, "retail")
    assert metrics["customer_count"] == 5  # John Smith, Jane Doe, Bob Wilson, Alice Brown, Charlie Davis
    assert metrics["repeat_customer_rate"] > 0
