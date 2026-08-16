"""Tests for the data profiling service."""

import pandas as pd
import pytest

from app.services.profiling import profile_dataframe


class TestProfileCleanData:
    """Tests using the clean_sales.csv fixture."""

    def test_row_count(self, clean_sales_df: pd.DataFrame) -> None:
        result = profile_dataframe(clean_sales_df)
        assert result["row_count"] == 12

    def test_no_duplicates(self, clean_sales_df: pd.DataFrame) -> None:
        result = profile_dataframe(clean_sales_df)
        assert result["duplicate_count"] == 0

    def test_column_count(self, clean_sales_df: pd.DataFrame) -> None:
        result = profile_dataframe(clean_sales_df)
        assert len(result["columns"]) == 6

    def test_column_names(self, clean_sales_df: pd.DataFrame) -> None:
        result = profile_dataframe(clean_sales_df)
        names = [c["column_name"] for c in result["columns"]]
        assert "Date" in names
        assert "Product" in names
        assert "Quantity" in names
        assert "Total" in names

    def test_date_column_detected(self, clean_sales_df: pd.DataFrame) -> None:
        result = profile_dataframe(clean_sales_df)
        date_col = next(c for c in result["columns"] if c["column_name"] == "Date")
        assert date_col["detected_type"] == "date"

    def test_numeric_columns_detected(self, clean_sales_df: pd.DataFrame) -> None:
        result = profile_dataframe(clean_sales_df)
        quantity = next(c for c in result["columns"] if c["column_name"] == "Quantity")
        assert quantity["detected_type"] == "numeric"

    def test_no_missing_values(self, clean_sales_df: pd.DataFrame) -> None:
        result = profile_dataframe(clean_sales_df)
        for col in result["columns"]:
            assert col["missing_count"] == 0
            assert col["missing_pct"] == 0.0

    def test_quality_score_perfect(self, clean_sales_df: pd.DataFrame) -> None:
        result = profile_dataframe(clean_sales_df)
        # Clean data, no duplicates, all types detected → near 100
        assert result["quality_score"] >= 95.0


class TestProfileMissingValues:
    """Tests using the missing_values.csv fixture."""

    def test_row_count(self, missing_values_df: pd.DataFrame) -> None:
        result = profile_dataframe(missing_values_df)
        assert result["row_count"] == 10

    def test_detects_missing_values(self, missing_values_df: pd.DataFrame) -> None:
        result = profile_dataframe(missing_values_df)
        # Product column has 2 missing values
        product_col = next(c for c in result["columns"] if c["column_name"] == "Product")
        assert product_col["missing_count"] == 2

    def test_missing_percentage(self, missing_values_df: pd.DataFrame) -> None:
        result = profile_dataframe(missing_values_df)
        product_col = next(c for c in result["columns"] if c["column_name"] == "Product")
        assert product_col["missing_pct"] == 20.0  # 2 out of 10

    def test_quality_score_lower(self, missing_values_df: pd.DataFrame) -> None:
        result = profile_dataframe(missing_values_df)
        # Missing values should lower the quality score
        assert result["quality_score"] < 100.0
        assert result["quality_score"] > 0.0

    def test_date_missing(self, missing_values_df: pd.DataFrame) -> None:
        result = profile_dataframe(missing_values_df)
        date_col = next(c for c in result["columns"] if c["column_name"] == "Date")
        assert date_col["missing_count"] == 1

    def test_customer_missing(self, missing_values_df: pd.DataFrame) -> None:
        result = profile_dataframe(missing_values_df)
        customer_col = next(c for c in result["columns"] if c["column_name"] == "Customer")
        assert customer_col["missing_count"] == 2


class TestProfileWrongTypes:
    """Tests using the wrong_types.csv fixture."""

    def test_detects_duplicates(self, wrong_types_df: pd.DataFrame) -> None:
        result = profile_dataframe(wrong_types_df)
        assert result["duplicate_count"] == 1  # One exact duplicate row

    def test_currency_columns_detected(self, wrong_types_df: pd.DataFrame) -> None:
        result = profile_dataframe(wrong_types_df)
        total_col = next(c for c in result["columns"] if c["column_name"] == "Total")
        assert total_col["detected_type"] == "currency"

    def test_quality_score_penalised_for_duplicates(self, wrong_types_df: pd.DataFrame) -> None:
        result = profile_dataframe(wrong_types_df)
        # Duplicates and type mismatches lower the score
        assert result["quality_score"] < 100.0


class TestProfileEdgeCases:
    """Edge case tests."""

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        with pytest.raises(Exception):
            # Empty DF with no columns should not profile silently
            profile_dataframe(df)

    def test_single_column(self) -> None:
        df = pd.DataFrame({"value": [1, 2, 3, 4, 5]})
        result = profile_dataframe(df)
        assert result["row_count"] == 5
        assert len(result["columns"]) == 1
        assert result["columns"][0]["detected_type"] == "numeric"

    def test_all_null_column(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [None, None, None]})
        result = profile_dataframe(df)
        null_col = next(c for c in result["columns"] if c["column_name"] == "b")
        assert null_col["missing_count"] == 3
        assert null_col["missing_pct"] == 100.0
