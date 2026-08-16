"""Deterministic insight rules — threshold-based, no LLM."""

from __future__ import annotations

from typing import Any


def generate_insights(metrics: dict[str, Any]) -> list[dict[str, str]]:
    """Generate deterministic insight strings from computed metrics.

    Each insight has a 'text' and 'category' (growth | profitability | anomaly | product).
    """
    insights: list[dict[str, str]] = []

    # --- Growth insights ---
    growth = metrics.get("growth_pct")
    if growth is not None:
        if growth > 10:
            insights.append({
                "text": f"Revenue is growing strongly at {growth:.1f}% month-over-month.",
                "category": "growth",
            })
        elif growth > 0:
            insights.append({
                "text": f"Revenue grew {growth:.1f}% compared to the prior period — steady but modest growth.",
                "category": "growth",
            })
        elif growth == 0:
            insights.append({
                "text": "Revenue is flat compared to the prior period.",
                "category": "growth",
            })
        elif growth > -10:
            insights.append({
                "text": f"Revenue declined {abs(growth):.1f}% from the prior period — worth investigating.",
                "category": "growth",
            })
        else:
            insights.append({
                "text": f"Revenue dropped significantly ({growth:.1f}%) — immediate attention recommended.",
                "category": "growth",
            })
    elif metrics.get("revenue") is not None:
        insights.append({
            "text": "Not enough data periods to calculate revenue growth — upload more months to enable trend analysis.",
            "category": "growth",
        })

    # --- Profitability insights ---
    profit_margin = metrics.get("profit_margin")
    if profit_margin is not None:
        if profit_margin > 20:
            insights.append({
                "text": f"Profit margin is healthy at {profit_margin:.1f}%.",
                "category": "profitability",
            })
        elif profit_margin > 10:
            insights.append({
                "text": f"Profit margin is {profit_margin:.1f}% — decent but there may be room to improve.",
                "category": "profitability",
            })
        elif profit_margin > 0:
            insights.append({
                "text": f"Profit margin is thin at {profit_margin:.1f}% — review cost structure for savings.",
                "category": "profitability",
            })
        else:
            insights.append({
                "text": f"Operating at a loss (margin: {profit_margin:.1f}%) — costs exceed revenue.",
                "category": "profitability",
            })

    profit = metrics.get("profit")
    revenue = metrics.get("revenue")
    if profit is not None and revenue is not None and revenue > 0:
        # Check if profit growth trails revenue growth
        if growth is not None and growth > 0 and profit_margin is not None:
            # Simple heuristic: if margin is below the "expected" range
            if profit_margin < 10 and growth > 5:
                insights.append({
                    "text": "Profit is growing slower than revenue — costs may be rising faster than sales.",
                    "category": "profitability",
                })

    # --- Product insights ---
    top_products = metrics.get("top_products", [])
    if top_products:
        top = top_products[0]
        if top["pct_of_total"] > 50:
            insights.append({
                "text": f"'{top['product']}' accounts for {top['pct_of_total']:.0f}% of total revenue — high concentration risk.",
                "category": "product",
            })
        elif len(top_products) >= 2:
            insights.append({
                "text": f"Top seller: '{top['product']}' at {top['pct_of_total']:.0f}% of revenue. Revenue is reasonably diversified across products.",
                "category": "product",
            })

    # --- Anomaly insights ---
    revenue_by_day = metrics.get("revenue_by_day", [])
    if len(revenue_by_day) >= 7:
        revenues = [d["revenue"] for d in revenue_by_day]
        anomalies = []
        for i in range(6, len(revenues)):
            trailing_avg = sum(revenues[i - 7 : i]) / 7
            if trailing_avg > 0 and revenues[i] < trailing_avg * 0.5:
                anomalies.append(revenue_by_day[i]["date"])

        if anomalies:
            if len(anomalies) == 1:
                insights.append({
                    "text": f"Unusual revenue drop on {anomalies[0]} — less than 50% of the trailing 7-day average.",
                    "category": "anomaly",
                })
            else:
                insights.append({
                    "text": f"{len(anomalies)} days with revenue below 50% of the trailing 7-day average — check for data gaps or seasonal patterns.",
                    "category": "anomaly",
                })

    # --- Customer insights ---
    repeat_rate = metrics.get("repeat_customer_rate")
    customer_count = metrics.get("customer_count")
    if repeat_rate is not None and customer_count is not None:
        if repeat_rate > 50:
            insights.append({
                "text": f"Strong customer loyalty: {repeat_rate:.0f}% of your {customer_count} customers are repeat buyers.",
                "category": "growth",
            })
        elif repeat_rate > 20:
            insights.append({
                "text": f"{repeat_rate:.0f}% repeat customer rate — moderate loyalty. Consider retention campaigns.",
                "category": "growth",
            })
        elif customer_count > 0:
            insights.append({
                "text": f"Low repeat customer rate ({repeat_rate:.0f}%) — focus on retention to build recurring revenue.",
                "category": "growth",
            })

    # Fallback if no insights generated
    if not insights:
        insights.append({
            "text": "Upload more data with additional columns (dates, products, costs) to unlock deeper insights.",
            "category": "growth",
        })

    return insights
