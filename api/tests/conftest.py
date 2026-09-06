"""Shared pytest fixtures for BizLens API tests."""

from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def clean_sales_df() -> pd.DataFrame:
    """Load the clean sales fixture."""
    return pd.read_csv(FIXTURES_DIR / "clean_sales.csv")


@pytest.fixture
def missing_values_df() -> pd.DataFrame:
    """Load the fixture with missing values."""
    return pd.read_csv(FIXTURES_DIR / "missing_values.csv")


@pytest.fixture
def wrong_types_df() -> pd.DataFrame:
    """Load the fixture with wrong types and duplicates."""
    return pd.read_csv(FIXTURES_DIR / "wrong_types.csv")


@pytest.fixture
def alt_headers_df() -> pd.DataFrame:
    """Load the alt-headers fixture (Order Date, Item, Units Sold, Sale Amount, Client)."""
    return pd.read_csv(FIXTURES_DIR / "alt_headers.csv")


@pytest.fixture
def no_cost_df() -> pd.DataFrame:
    """Load the no-cost fixture (Transaction Date, Service, Revenue, Customer ID)."""
    return pd.read_csv(FIXTURES_DIR / "no_cost.csv")


@pytest.fixture
def messy_dates_df() -> pd.DataFrame:
    """Load the messy-dates fixture (Booking Date with mixed formats)."""
    return pd.read_csv(FIXTURES_DIR / "messy_dates.csv")
