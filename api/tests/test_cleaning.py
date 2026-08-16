"""Tests for data cleaning service."""

import pandas as pd
import pytest

from app.services.cleaning import clean_dataframe


def test_clean_removes_duplicates(wrong_types_df: pd.DataFrame):
    result = clean_dataframe(wrong_types_df)
    assert result["summary"]["duplicates_removed"] == 1
    assert len(result["cleaned_df"]) == len(wrong_types_df) - 1


def test_clean_imputes_missing_values(missing_values_df: pd.DataFrame):
    result = clean_dataframe(missing_values_df)
    df = result["cleaned_df"]
    # Categoricals replaced with 'Unknown'
    assert not df["Product"].isna().any()
    assert (df["Product"] == "Unknown").sum() == 2
    # Numeric median imputed
    assert not df["Quantity"].isna().any()


def test_clean_normalizes_currency(wrong_types_df: pd.DataFrame):
    result = clean_dataframe(wrong_types_df)
    df = result["cleaned_df"]
    # Total column should be converted to numeric float
    assert pd.api.types.is_numeric_dtype(df["Total"])
    assert df["Total"].iloc[0] == 250.0
