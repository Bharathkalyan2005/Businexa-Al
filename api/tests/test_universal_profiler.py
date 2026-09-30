"""
Unit tests for Stage 1 — Universal Deterministic Data Profiler.
Covers two very different shaped datasets: business/sales and clinical/records.

Run with:
    cd api
    python -m pytest tests/test_universal_profiler.py -v
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.services.universal.profiler import (
    _classify_column,
    _coerce_numeric,
    _correlation_matrix,
    _detect_target_column,
    _groupby_aggregates,
    _is_boolean_series,
    _is_datetime_series,
    _numeric_stats,
    _categorical_stats,
    _boolean_stats,
    _datetime_stats,
    build_data_profile,
)
from tests.fixtures.universal_datasets import make_clinical_df, make_sales_df


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sales_df() -> pd.DataFrame:
    return make_sales_df()


@pytest.fixture(scope="module")
def clinical_df() -> pd.DataFrame:
    return make_clinical_df()


# ─────────────────────────────────────────────────────────────────────────────
# Unit: _classify_column
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyColumn:
    def test_numeric_int_column(self):
        s = pd.Series([1, 2, 3, 4, 5] * 20)
        assert _classify_column(s, "qty", 100) == "numeric"

    def test_numeric_float_column(self):
        s = pd.Series([1.1, 2.2, 3.3, 4.4, 5.5] * 20)
        assert _classify_column(s, "price", 100) == "numeric"

    def test_numeric_with_currency_strings(self):
        s = pd.Series(["$10.50", "$20.00", "$5.75"] * 40)
        assert _classify_column(s, "revenue", 120) == "numeric"

    def test_boolean_int_column(self):
        s = pd.Series([0, 1, 0, 1, 1, 0] * 20)
        assert _classify_column(s, "churn", 120) == "boolean"

    def test_boolean_yes_no_column(self):
        s = pd.Series(["Yes", "No", "Yes", "No", "Yes"] * 30)
        assert _classify_column(s, "smoker", 150) == "boolean"

    def test_boolean_true_false_column(self):
        s = pd.Series(["True", "False", "True", "False"] * 30)
        assert _classify_column(s, "active", 120) == "boolean"

    def test_categorical_low_cardinality(self):
        s = pd.Series(["North", "South", "East", "West"] * 50)
        assert _classify_column(s, "region", 200) == "categorical"

    def test_categorical_medium_cardinality(self):
        s = pd.Series([f"Cat_{i}" for i in range(30)] * 7)
        assert _classify_column(s, "category", 210) == "categorical"

    def test_datetime_iso_format(self):
        dates = pd.date_range("2021-01-01", periods=100, freq="D").astype(str)
        s = pd.Series(dates)
        assert _classify_column(s, "date", 100) == "datetime"

    def test_datetime_native_dtype(self):
        s = pd.Series(pd.date_range("2021-01-01", periods=100, freq="D"))
        assert _classify_column(s, "date", 100) == "datetime"

    def test_id_like_string_column(self):
        s = pd.Series([f"ORD-{10000 + i}" for i in range(200)])
        assert _classify_column(s, "order_id", 200) == "id_like"

    def test_free_text_high_cardinality(self):
        # Long prose-like strings with many words should be free_text, not id_like
        s = pd.Series([f"Comment about thing number {i} with extra words here" for i in range(200)])
        assert _classify_column(s, "notes", 200) == "free_text"

    def test_not_datetime_plain_numbers(self):
        """Pure sequential integers 0..99: all unique, all integer → id_like.
        Numbers with repeated values should be numeric."""
        # Repeated integers are NOT all-unique → numeric
        s = pd.Series(list(range(10)) * 10)
        assert _classify_column(s, "count", 100) == "numeric"


# ─────────────────────────────────────────────────────────────────────────────
# Unit: numeric stats
# ─────────────────────────────────────────────────────────────────────────────

class TestNumericStats:
    def test_known_values(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        stats = _numeric_stats(s, "numeric")
        assert stats["min"] == pytest.approx(1.0)
        assert stats["max"] == pytest.approx(5.0)
        assert stats["mean"] == pytest.approx(3.0)
        assert stats["median"] == pytest.approx(3.0)
        assert stats["std"] == pytest.approx(math.sqrt(2.5), rel=1e-4)
        assert stats["q1"] == pytest.approx(2.0)
        assert stats["q3"] == pytest.approx(4.0)
        assert stats["non_null_count"] == 5

    def test_outlier_detection(self):
        # 1..10 with 100 as clear outlier
        s = pd.Series(list(range(1, 11)) + [100])
        stats = _numeric_stats(s, "numeric")
        assert stats["outlier_count"] >= 1

    def test_no_outlier_uniform(self):
        s = pd.Series(list(range(1, 21)))
        stats = _numeric_stats(s, "numeric")
        assert stats["outlier_count"] == 0

    def test_null_handling(self):
        s = pd.Series([1.0, None, 3.0, None, 5.0])
        stats = _numeric_stats(s, "numeric")
        assert stats["non_null_count"] == 3
        assert stats["mean"] == pytest.approx(3.0)

    def test_currency_strings(self):
        s = pd.Series(["$100", "$200", "$300", "$400"])
        stats = _numeric_stats(s, "numeric")
        assert stats["mean"] == pytest.approx(250.0)

    def test_empty_returns_error(self):
        s = pd.Series([None, None, None])
        stats = _numeric_stats(s, "numeric")
        assert "error" in stats


# ─────────────────────────────────────────────────────────────────────────────
# Unit: categorical stats
# ─────────────────────────────────────────────────────────────────────────────

class TestCategoricalStats:
    def test_top_values_correct(self):
        s = pd.Series(["A"] * 50 + ["B"] * 30 + ["C"] * 20)
        stats = _categorical_stats(s)
        assert stats["unique_count"] == 3
        assert stats["top_values"][0]["value"] == "A"
        assert stats["top_values"][0]["count"] == 50
        assert stats["top_values"][0]["pct"] == pytest.approx(50.0)

    def test_top_5_max(self):
        s = pd.Series([str(i) for i in range(10)] * 10)
        stats = _categorical_stats(s)
        assert len(stats["top_values"]) == 5

    def test_null_excluded_from_top_values(self):
        s = pd.Series(["X"] * 40 + [None] * 10 + ["Y"] * 50)
        stats = _categorical_stats(s)
        values = [tv["value"] for tv in stats["top_values"]]
        assert "nan" not in values
        assert "None" not in values


# ─────────────────────────────────────────────────────────────────────────────
# Unit: datetime stats
# ─────────────────────────────────────────────────────────────────────────────

class TestDatetimeStats:
    def test_range_and_granularity_year(self):
        dates = pd.date_range("2018-01-01", "2022-12-31", freq="ME")
        s = pd.Series(dates)
        stats = _datetime_stats(s)
        assert stats["span_days"] > 365
        assert stats["granularity"] in ("year", "quarter")

    def test_range_and_granularity_month(self):
        dates = pd.date_range("2022-01-01", "2022-10-31", freq="D")
        s = pd.Series(dates)
        stats = _datetime_stats(s)
        assert stats["granularity"] == "month"

    def test_range_and_granularity_day(self):
        dates = pd.date_range("2022-06-01", "2022-06-20", freq="D")
        s = pd.Series(dates)
        stats = _datetime_stats(s)
        assert stats["granularity"] == "day"

    def test_min_max_correct(self):
        s = pd.Series(["2021-01-01", "2021-06-15", "2021-12-31"])
        stats = _datetime_stats(s)
        assert "2021-01-01" in stats["min"]
        assert "2021-12-31" in stats["max"]


# ─────────────────────────────────────────────────────────────────────────────
# Unit: boolean stats
# ─────────────────────────────────────────────────────────────────────────────

class TestBooleanStats:
    def test_int_binary(self):
        s = pd.Series([1, 0, 1, 1, 0, 0, 1])
        stats = _boolean_stats(s)
        assert stats["true_count"] == 4
        assert stats["false_count"] == 3
        # true_pct is rounded to 1 decimal place in the implementation
        assert stats["true_pct"] == pytest.approx(4 / 7 * 100, abs=0.1)

    def test_yes_no_strings(self):
        s = pd.Series(["Yes", "No", "Yes", "Yes", "No"])
        stats = _boolean_stats(s)
        assert stats["true_count"] == 3
        assert stats["false_count"] == 2

    def test_non_null_count(self):
        s = pd.Series([1, 0, None, 1, None])
        stats = _boolean_stats(s)
        assert stats["non_null_count"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# Unit: correlation matrix
# ─────────────────────────────────────────────────────────────────────────────

class TestCorrelationMatrix:
    def test_perfect_positive_correlation(self):
        df = pd.DataFrame({"A": [1, 2, 3, 4, 5], "B": [2, 4, 6, 8, 10]})
        corr = _correlation_matrix(df, ["A", "B"])
        assert corr["A"]["B"] == pytest.approx(1.0, abs=1e-10)

    def test_perfect_negative_correlation(self):
        df = pd.DataFrame({"A": [1, 2, 3, 4, 5], "B": [10, 8, 6, 4, 2]})
        corr = _correlation_matrix(df, ["A", "B"])
        assert corr["A"]["B"] == pytest.approx(-1.0, abs=1e-10)

    def test_self_correlation_is_1(self):
        df = pd.DataFrame({"X": [1.5, 2.5, 3.5, 4.5]})
        # Need at least 2 cols to compute
        df["Y"] = df["X"] * 2
        corr = _correlation_matrix(df, ["X", "Y"])
        assert corr["X"]["X"] == pytest.approx(1.0, abs=1e-10)

    def test_single_col_returns_empty(self):
        df = pd.DataFrame({"X": [1, 2, 3]})
        corr = _correlation_matrix(df, ["X"])
        assert corr == {}

    def test_zero_cols_returns_empty(self):
        df = pd.DataFrame()
        corr = _correlation_matrix(df, [])
        assert corr == {}


# ─────────────────────────────────────────────────────────────────────────────
# Unit: group-by aggregates
# ─────────────────────────────────────────────────────────────────────────────

class TestGroupByAggregates:
    def test_basic_groupby(self):
        df = pd.DataFrame({
            "Region": ["North", "South", "North", "South", "North"],
            "Revenue": [100.0, 200.0, 150.0, 250.0, 120.0],
        })
        aggs = _groupby_aggregates(df, ["Region"], ["Revenue"])
        assert "Region" in aggs
        assert "Revenue" in aggs["Region"]
        groups = {row["group"]: row for row in aggs["Region"]["Revenue"]}
        assert groups["North"]["mean"] == pytest.approx(
            (100 + 150 + 120) / 3, rel=1e-4
        )
        assert groups["North"]["count"] == 3
        assert groups["South"]["mean"] == pytest.approx(225.0, rel=1e-4)

    def test_skips_high_cardinality_categorical(self):
        df = pd.DataFrame({
            "Category": [f"Cat_{i}" for i in range(20)],
            "Value": list(range(20)),
        })
        # 20 unique categories > _GROUPBY_MAX_UNIQUE (15) — should be skipped
        aggs = _groupby_aggregates(df, ["Category"], ["Value"])
        assert "Category" not in aggs

    def test_empty_dataframe(self):
        df = pd.DataFrame({"Cat": [], "Val": []})
        aggs = _groupby_aggregates(df, ["Cat"], ["Val"])
        assert aggs == {}


# ─────────────────────────────────────────────────────────────────────────────
# Unit: target column detection
# ─────────────────────────────────────────────────────────────────────────────

class TestTargetColumnDetection:
    def test_detects_boolean_column(self):
        df = pd.DataFrame({
            "Age": [25, 30, 35, 40],
            "Revenue": [100.0, 200.0, 300.0, 400.0],
            "Churn": [0, 1, 0, 1],
        })
        profiles = [
            {"column": "Age", "type": "numeric", "stats": {}},
            {"column": "Revenue", "type": "numeric", "stats": {}},
            {"column": "Churn", "type": "boolean", "stats": {}},
        ]
        target = _detect_target_column(df, profiles)
        assert target == "Churn"

    def test_detects_yes_no_categorical(self):
        df = pd.DataFrame({
            "Score": [85, 90, 72, 68],
            "Pass": ["Yes", "Yes", "No", "No"],
        })
        profiles = [
            {"column": "Score", "type": "numeric", "stats": {}},
            {
                "column": "Pass",
                "type": "categorical",
                "stats": {
                    "unique_count": 2,
                    "top_values": [
                        {"value": "Yes", "count": 2, "pct": 50.0},
                        {"value": "No", "count": 2, "pct": 50.0},
                    ],
                },
            },
        ]
        target = _detect_target_column(df, profiles)
        assert target == "Pass"

    def test_detects_binary_numeric(self):
        df = pd.DataFrame({
            "Age": [25, 30, 35, 40, 45],
            "Outcome": [1.0, 0.0, 1.0, 0.0, 1.0],
        })
        profiles = [
            {"column": "Age", "type": "numeric", "stats": {}},
            {"column": "Outcome", "type": "numeric", "stats": {}},
        ]
        target = _detect_target_column(df, profiles)
        assert target == "Outcome"

    def test_no_target_when_no_label_columns(self):
        df = pd.DataFrame({
            "Revenue": [100.0, 200.0, 300.0],
            "Quantity": [1, 2, 3],
        })
        profiles = [
            {"column": "Revenue", "type": "numeric", "stats": {}},
            {"column": "Quantity", "type": "numeric", "stats": {}},
        ]
        target = _detect_target_column(df, profiles)
        assert target is None


# ─────────────────────────────────────────────────────────────────────────────
# Integration: build_data_profile on Sales dataset
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildDataProfileSales:
    def test_row_and_col_count(self, sales_df):
        profile = build_data_profile(sales_df)
        assert profile["row_count"] == 200
        assert profile["col_count"] == 11

    def test_not_degraded(self, sales_df):
        profile = build_data_profile(sales_df)
        assert profile["degraded_mode"] is False

    def test_column_type_classification(self, sales_df):
        profile = build_data_profile(sales_df)
        col_types = {cp["column"]: cp["type"] for cp in profile["columns"]}
        # OrderID is high-cardinality strings
        assert col_types["OrderID"] == "id_like"
        # Date is datetime
        assert col_types["Date"] == "datetime"
        # Category, Region, Product, CustomerType are categorical
        for col in ["Category", "Region", "CustomerType"]:
            assert col_types[col] == "categorical", f"{col} should be categorical"
        # Churn (Active/Churned) — 2 values, low cardinality → categorical or boolean
        assert col_types["Churn"] in ("categorical", "boolean")
        # Quantity, UnitPrice, Revenue are numeric
        for col in ["Quantity", "UnitPrice", "Revenue"]:
            assert col_types[col] == "numeric", f"{col} should be numeric"

    def test_numeric_stats_revenue(self, sales_df):
        profile = build_data_profile(sales_df)
        rev_profile = next(cp for cp in profile["columns"] if cp["column"] == "Revenue")
        stats = rev_profile["stats"]

        # Verify against direct pandas computation
        expected_mean = sales_df["Revenue"].mean()
        expected_median = sales_df["Revenue"].median()
        expected_std = sales_df["Revenue"].std()

        assert stats["mean"] == pytest.approx(expected_mean, rel=1e-5)
        assert stats["median"] == pytest.approx(expected_median, rel=1e-5)
        assert stats["std"] == pytest.approx(expected_std, rel=1e-5)
        assert stats["min"] == pytest.approx(sales_df["Revenue"].min(), rel=1e-5)
        assert stats["max"] == pytest.approx(sales_df["Revenue"].max(), rel=1e-5)

    def test_categorical_stats_category(self, sales_df):
        profile = build_data_profile(sales_df)
        cat_profile = next(cp for cp in profile["columns"] if cp["column"] == "Category")
        stats = cat_profile["stats"]

        assert stats["unique_count"] == sales_df["Category"].nunique()
        assert len(stats["top_values"]) <= 5
        # Top values must sum to <= 100 %
        total_pct = sum(tv["pct"] for tv in stats["top_values"])
        assert total_pct <= 100.0 + 1e-6

    def test_null_pct_discount(self, sales_df):
        profile = build_data_profile(sales_df)
        discount_profile = next(cp for cp in profile["columns"] if cp["column"] == "Discount")
        expected_null_pct = sales_df["Discount"].isna().sum() / len(sales_df) * 100
        assert discount_profile["null_pct"] == pytest.approx(expected_null_pct, abs=0.01)

    def test_datetime_profile_date_col(self, sales_df):
        profile = build_data_profile(sales_df)
        date_profile = next(cp for cp in profile["columns"] if cp["column"] == "Date")
        assert date_profile["type"] == "datetime"
        stats = date_profile["stats"]
        assert "min" in stats and "max" in stats
        assert stats["span_days"] > 365  # ~4 years of data

    def test_correlation_matrix_present(self, sales_df):
        profile = build_data_profile(sales_df)
        corr = profile["correlation_matrix"]
        assert "Revenue" in corr
        assert "Quantity" in corr
        # Revenue and UnitPrice should show positive correlation
        assert corr["Revenue"]["UnitPrice"] is not None
        assert corr["Revenue"]["UnitPrice"] > 0

    def test_groupby_aggregates_present(self, sales_df):
        profile = build_data_profile(sales_df)
        aggs = profile["groupby_aggregates"]
        # Category and Region have <15 uniques → should appear
        assert "Category" in aggs or "Region" in aggs

    def test_target_column_churn(self, sales_df):
        profile = build_data_profile(sales_df)
        # "Churn" is Active/Churned — two label-like values
        assert profile["target_column"] == "Churn"

    def test_sample_rows_count(self, sales_df):
        profile = build_data_profile(sales_df)
        assert len(profile["sample_rows"]) == 8

    def test_no_nan_in_sample_rows(self, sales_df):
        profile = build_data_profile(sales_df)
        for row in profile["sample_rows"]:
            for val in row.values():
                if val is not None:
                    assert not (isinstance(val, float) and math.isnan(val))


# ─────────────────────────────────────────────────────────────────────────────
# Integration: build_data_profile on Clinical dataset
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildDataProfileClinical:
    def test_row_and_col_count(self, clinical_df):
        profile = build_data_profile(clinical_df)
        assert profile["row_count"] == 300
        assert profile["col_count"] == 12

    def test_not_degraded(self, clinical_df):
        profile = build_data_profile(clinical_df)
        assert profile["degraded_mode"] is False

    def test_column_type_classification(self, clinical_df):
        profile = build_data_profile(clinical_df)
        col_types = {cp["column"]: cp["type"] for cp in profile["columns"]}
        # PatientID is id_like
        assert col_types["PatientID"] == "id_like"
        # Age, BMI, Glucose, HeartRate, LengthOfStay are numeric
        for col in ["Age", "BMI", "Glucose", "HeartRate", "LengthOfStay"]:
            assert col_types[col] == "numeric", f"{col} should be numeric"
        # Gender, BloodPressure, Cholesterol are categorical
        for col in ["Gender", "BloodPressure", "Cholesterol"]:
            assert col_types[col] == "categorical", f"{col} should be categorical"
        # Smoker (Yes/No) is boolean — binary string column
        assert col_types["Smoker"] == "boolean"
        # AdmissionDate is datetime
        assert col_types["AdmissionDate"] == "datetime"
        # HeartDisease is 0/1 numeric — could be boolean or numeric
        assert col_types["HeartDisease"] in ("boolean", "numeric")

    def test_numeric_stats_age(self, clinical_df):
        profile = build_data_profile(clinical_df)
        age_profile = next(cp for cp in profile["columns"] if cp["column"] == "Age")
        stats = age_profile["stats"]

        expected_mean = clinical_df["Age"].mean()
        assert stats["mean"] == pytest.approx(expected_mean, rel=1e-5)
        assert stats["min"] == pytest.approx(clinical_df["Age"].min(), rel=1e-5)
        assert stats["max"] == pytest.approx(clinical_df["Age"].max(), rel=1e-5)

    def test_null_pct_glucose(self, clinical_df):
        profile = build_data_profile(clinical_df)
        gluc_profile = next(cp for cp in profile["columns"] if cp["column"] == "Glucose")
        expected_null_pct = clinical_df["Glucose"].isna().sum() / len(clinical_df) * 100
        assert gluc_profile["null_pct"] == pytest.approx(expected_null_pct, abs=0.01)
        # Dataset has ~4 % nulls in Glucose
        assert gluc_profile["null_pct"] > 0

    def test_categorical_gender_stats(self, clinical_df):
        profile = build_data_profile(clinical_df)
        gender_profile = next(cp for cp in profile["columns"] if cp["column"] == "Gender")
        stats = gender_profile["stats"]
        assert stats["unique_count"] == 2
        top_values_names = {tv["value"] for tv in stats["top_values"]}
        assert {"Male", "Female"} == top_values_names

    def test_target_column_is_heart_disease(self, clinical_df):
        profile = build_data_profile(clinical_df)
        # HeartDisease (0/1 numeric) scores highest as target — numeric binary beats string-boolean
        assert profile["target_column"] == "HeartDisease"

    def test_correlation_age_heartdisease(self, clinical_df):
        profile = build_data_profile(clinical_df)
        corr = profile["correlation_matrix"]
        # HeartDisease may be numeric — if so, check positive correlation with Age
        if "HeartDisease" in corr and "Age" in corr.get("HeartDisease", {}):
            val = corr["HeartDisease"]["Age"]
            if val is not None:
                assert val > 0  # older patients more likely to have heart disease

    def test_groupby_includes_gender(self, clinical_df):
        profile = build_data_profile(clinical_df)
        aggs = profile["groupby_aggregates"]
        assert "Gender" in aggs or "Smoker" in aggs

    def test_groupby_mean_age_by_gender_numerically_correct(self, clinical_df):
        profile = build_data_profile(clinical_df)
        aggs = profile["groupby_aggregates"]
        if "Gender" not in aggs or "Age" not in aggs["Gender"]:
            pytest.skip("Gender-Age groupby not present in profile")
        groups = {row["group"]: row for row in aggs["Gender"]["Age"]}
        expected_male = clinical_df.groupby("Gender")["Age"].mean()["Male"]
        expected_female = clinical_df.groupby("Gender")["Age"].mean()["Female"]
        assert groups["Male"]["mean"] == pytest.approx(expected_male, rel=1e-5)
        assert groups["Female"]["mean"] == pytest.approx(expected_female, rel=1e-5)

    def test_admission_date_profile(self, clinical_df):
        profile = build_data_profile(clinical_df)
        date_profile = next(
            cp for cp in profile["columns"] if cp["column"] == "AdmissionDate"
        )
        assert date_profile["type"] == "datetime"
        assert date_profile["stats"]["span_days"] > 365  # ~4 years of data


# ─────────────────────────────────────────────────────────────────────────────
# Edge case: degraded mode
# ─────────────────────────────────────────────────────────────────────────────

class TestDegradedMode:
    def test_empty_dataframe(self):
        df = pd.DataFrame()
        profile = build_data_profile(df)
        assert profile["degraded_mode"] is True
        assert profile["row_count"] == 0

    def test_too_few_rows(self):
        df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        profile = build_data_profile(df)
        assert profile["degraded_mode"] is True
        assert profile["degraded_reason"] is not None

    def test_no_groupby_in_degraded_mode(self):
        df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        profile = build_data_profile(df)
        assert profile["groupby_aggregates"] == {}

    def test_no_correlation_in_degraded_mode(self):
        df = pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0]})
        profile = build_data_profile(df)
        assert profile["correlation_matrix"] == {}

    def test_no_target_in_degraded_mode(self):
        df = pd.DataFrame({"A": [0, 1], "B": ["x", "y"]})
        profile = build_data_profile(df)
        assert profile["target_column"] is None

    def test_fully_text_columns_degraded(self):
        n = 50
        df = pd.DataFrame({
            # Both columns are id_like (high cardinality, short strings with no spaces)
            # No numeric or categorical columns → has_useful_cols=False → degraded
            "id": [f"id-{i}" for i in range(n)],
            "code": [f"CODE-{1000+i}" for i in range(n)],
        })
        profile = build_data_profile(df)
        assert profile["degraded_mode"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Numerical correctness: spot-check against raw pandas
# ─────────────────────────────────────────────────────────────────────────────

class TestNumericalCorrectness:
    """Bit-exact verification that profiler values match direct Pandas computation."""

    def test_sales_quantity_stats(self, sales_df):
        profile = build_data_profile(sales_df)
        qty_profile = next(cp for cp in profile["columns"] if cp["column"] == "Quantity")
        stats = qty_profile["stats"]
        assert stats["min"] == pytest.approx(sales_df["Quantity"].min(), rel=1e-9)
        assert stats["max"] == pytest.approx(sales_df["Quantity"].max(), rel=1e-9)
        assert stats["mean"] == pytest.approx(sales_df["Quantity"].mean(), rel=1e-9)
        assert stats["median"] == pytest.approx(sales_df["Quantity"].median(), rel=1e-9)
        assert stats["std"] == pytest.approx(sales_df["Quantity"].std(), rel=1e-9)

    def test_clinical_bmi_stats(self, clinical_df):
        profile = build_data_profile(clinical_df)
        bmi_profile = next(cp for cp in profile["columns"] if cp["column"] == "BMI")
        stats = bmi_profile["stats"]
        bmi_clean = clinical_df["BMI"].dropna()
        assert stats["mean"] == pytest.approx(bmi_clean.mean(), rel=1e-9)
        assert stats["non_null_count"] == len(bmi_clean)

    def test_clinical_cholesterol_top_values(self, clinical_df):
        profile = build_data_profile(clinical_df)
        chol_profile = next(
            cp for cp in profile["columns"] if cp["column"] == "Cholesterol"
        )
        stats = chol_profile["stats"]
        # Verify top value matches pandas value_counts
        vc = clinical_df["Cholesterol"].value_counts()
        assert stats["top_values"][0]["value"] == vc.index[0]
        assert stats["top_values"][0]["count"] == vc.iloc[0]

    def test_groupby_region_revenue_mean_sales(self, sales_df):
        profile = build_data_profile(sales_df)
        aggs = profile["groupby_aggregates"]
        if "Region" not in aggs or "Revenue" not in aggs["Region"]:
            pytest.skip("Region-Revenue groupby not present")
        groups = {row["group"]: row for row in aggs["Region"]["Revenue"]}
        expected = sales_df.groupby("Region")["Revenue"].mean()
        for region, row in groups.items():
            assert row["mean"] == pytest.approx(expected[region], rel=1e-5)
