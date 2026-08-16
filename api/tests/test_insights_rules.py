"""Tests for deterministic insight rules."""

from app.services.analytics.insights_rules import generate_insights


def test_growth_insights():
    metrics = {"growth_pct": 15.5, "revenue": 10000}
    insights = generate_insights(metrics)
    assert any("growing strongly" in i["text"] for i in insights)


def test_profit_margin_insights():
    metrics = {"profit_margin": 25.0, "profit": 2500, "revenue": 10000}
    insights = generate_insights(metrics)
    assert any("healthy" in i["text"] for i in insights)


def test_top_product_concentration_insight():
    metrics = {
        "top_products": [{"product": "Widget A", "revenue": 800, "pct_of_total": 80.0}],
    }
    insights = generate_insights(metrics)
    assert any("concentration risk" in i["text"] for i in insights)
