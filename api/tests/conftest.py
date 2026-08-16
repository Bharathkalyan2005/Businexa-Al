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
