"""Per-business-type metric configurations."""

from __future__ import annotations

from typing import Any

# Maps business_type to the metric categories that are especially relevant.
# All basic metrics (revenue, orders, AOV) are always computed.
# These configs control which *extra* metrics are attempted.
BUSINESS_TYPE_CONFIGS: dict[str, dict[str, Any]] = {
    "retail": {
        "label": "Retail",
        "extra_metrics": ["inventory_turnover", "stock_velocity"],
        "expected_columns": {
            "product": ["product", "item", "sku", "product_name", "item_name"],
            "quantity": ["quantity", "qty", "units", "units_sold"],
            "cost": ["cost", "cogs", "unit_cost", "cost_price"],
        },
    },
    "restaurant": {
        "label": "Restaurant",
        "extra_metrics": ["food_cost_ratio", "avg_table_size"],
        "expected_columns": {
            "product": ["item", "dish", "menu_item", "product"],
            "cost": ["food_cost", "cost", "cogs", "ingredient_cost"],
        },
    },
    "salon": {
        "label": "Salon",
        "extra_metrics": ["avg_service_value", "client_retention"],
        "expected_columns": {
            "product": ["service", "treatment", "product", "item"],
            "customer": ["client", "customer", "customer_name", "client_name"],
        },
    },
    "cleaning_service": {
        "label": "Cleaning Service",
        "extra_metrics": ["avg_job_value", "repeat_client_rate"],
        "expected_columns": {
            "product": ["service", "job_type", "service_type", "product"],
            "customer": ["client", "customer", "customer_name", "account"],
        },
    },
    "ecommerce": {
        "label": "E-commerce",
        "extra_metrics": ["cart_abandonment", "return_rate"],
        "expected_columns": {
            "product": ["product", "item", "sku", "product_name"],
            "quantity": ["quantity", "qty", "units"],
            "customer": ["customer", "customer_email", "buyer", "customer_id"],
        },
    },
    "other": {
        "label": "Other",
        "extra_metrics": [],
        "expected_columns": {
            "product": ["product", "item", "service", "description"],
        },
    },
}


def resolve_column(
    df_columns: list[str],
    semantic_name: str,
    business_type: str,
) -> str | None:
    """Try to find a column in the DataFrame that matches a semantic role.

    Uses the business-type-specific expected column names, plus common fallbacks.
    Returns the first matching column name, or None.
    """
    config = BUSINESS_TYPE_CONFIGS.get(business_type, BUSINESS_TYPE_CONFIGS["other"])
    expected = config["expected_columns"].get(semantic_name, [])

    # Common fallbacks for all types
    common_fallbacks: dict[str, list[str]] = {
        "date": ["date", "order_date", "transaction_date", "sale_date", "created_at", "timestamp"],
        "revenue": ["total", "revenue", "amount", "sales", "total_amount", "sale_amount", "price", "total_price"],
        "product": ["product", "item", "service", "description", "product_name", "item_name"],
        "quantity": ["quantity", "qty", "units", "count", "units_sold"],
        "cost": ["cost", "cogs", "unit_cost", "cost_price", "total_cost"],
        "customer": ["customer", "client", "customer_name", "client_name", "buyer", "customer_id", "email"],
        "profit": ["profit", "net_profit", "margin", "net_income"],
    }

    candidates = list(expected) + common_fallbacks.get(semantic_name, [])

    # Normalise both sides to lowercase for matching
    df_cols_lower = {c.lower().strip(): c for c in df_columns}

    for candidate in candidates:
        if candidate.lower() in df_cols_lower:
            return df_cols_lower[candidate.lower()]

    return None
