"""Schema-agnostic pipeline tests — 3 structurally different sample files.

These tests verify requirement 6: the system must handle different headers,
different column order, a missing cost column, and messy date formats, and
produce correct role detection + dashboard output for each.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.analytics.engine import run_full_analysis
from app.services.analytics.metrics import compute_metrics
from app.services.cleaning import clean_dataframe
from app.services.column_roles import (
    ROLE_LABELS,
    detect_column_roles,
    suggest_ui_confirmations,
)
from app.services.profiling import profile_dataframe


# ---------------------------------------------------------------------------
# Fixture 1 — Alt Headers (Order Date / Item / Units Sold / Sale Amount / Client)
# ---------------------------------------------------------------------------


class TestAltHeaders:
    """Different header names, different column order, no cost column."""

    def test_date_role_detected_by_synonym(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        mapping = result["role_mapping"]
        assert mapping["date_column"] == "Order Date", (
            f"Expected 'Order Date' as date_column, got {mapping['date_column']!r}"
        )

    def test_amount_role_detected_by_synonym(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        mapping = result["role_mapping"]
        assert mapping["amount_column"] == "Sale Amount", (
            f"Expected 'Sale Amount' as amount_column, got {mapping['amount_column']!r}"
        )

    def test_category_role_detected_by_synonym(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        mapping = result["role_mapping"]
        assert mapping["category_column"] == "Item", (
            f"Expected 'Item' as category_column, got {mapping['category_column']!r}"
        )

    def test_quantity_role_detected_by_synonym(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        mapping = result["role_mapping"]
        assert mapping["quantity_column"] == "Units Sold", (
            f"Expected 'Units Sold' as quantity_column, got {mapping['quantity_column']!r}"
        )

    def test_id_role_detected_by_synonym(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        mapping = result["role_mapping"]
        assert mapping["id_column"] == "Client", (
            f"Expected 'Client' as id_column, got {mapping['id_column']!r}"
        )

    def test_cost_column_absent(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        mapping = result["role_mapping"]
        assert mapping.get("cost_column") is None, (
            f"Expected no cost_column, got {mapping.get('cost_column')!r}"
        )

    def test_dashboard_viable(self, alt_headers_df: pd.DataFrame) -> None:
        result = profile_dataframe(alt_headers_df, business_type="retail")
        assert result["dashboard_viable"] is True
        assert result["dashboard_error"] is None

    def test_revenue_computes_correctly(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        metrics = compute_metrics(
            alt_headers_df, "retail", auto_role_mapping=result["role_mapping"]
        )
        assert metrics["revenue"] is not None
        assert metrics["revenue"] > 0
        assert "revenue" in metrics["available_sections"]

    def test_top_products_uses_item_column(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        metrics = compute_metrics(
            alt_headers_df, "retail", auto_role_mapping=result["role_mapping"]
        )
        assert len(metrics["top_products"]) > 0
        # Products should come from the 'Item' column values
        product_names = {p["product"] for p in metrics["top_products"]}
        assert product_names.issubset({"Coffee Beans", "Tea Bags", "Filters"})

    def test_profit_skipped_with_message(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        metrics = compute_metrics(
            alt_headers_df, "retail", auto_role_mapping=result["role_mapping"]
        )
        assert metrics["profit"] is None
        assert metrics["profit_margin"] is None
        # Skipped metrics should include profit with an explanation
        skipped_keys = {s["metric"] for s in metrics["skipped_metrics"]}
        assert "profit" in skipped_keys, f"Expected 'profit' in skipped_metrics: {skipped_keys}"
        assert "profit_margin" in skipped_keys

    def test_pipeline_log_documents_role_decisions(self, alt_headers_df: pd.DataFrame) -> None:
        result = detect_column_roles(alt_headers_df, "retail")
        messages = [entry["message"] for entry in result["pipeline_log"]]
        # Should log at least the role mapping decisions
        assert any("date_column" in m for m in messages), "Expected date_column mapping in log"
        assert any("amount_column" in m for m in messages), "Expected amount_column mapping in log"

    def test_ui_confirmations_returned(self, alt_headers_df: pd.DataFrame) -> None:
        result = profile_dataframe(alt_headers_df, business_type="retail")
        # ui_confirmations is a list (may be empty for high-confidence detections)
        assert isinstance(result["ui_confirmations"], list)

    def test_full_analysis_does_not_crash(self, alt_headers_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(alt_headers_df, "retail")
        clean = clean_dataframe(alt_headers_df, role_mapping=role_result["role_mapping"])
        analysis = run_full_analysis(
            clean["cleaned_df"], "retail", auto_role_mapping=role_result["role_mapping"]
        )
        assert analysis["dashboard_viable"] is True
        assert isinstance(analysis["insights"], list)


# ---------------------------------------------------------------------------
# Fixture 2 — No Cost Column (Transaction Date / Service / Revenue / Customer ID)
# ---------------------------------------------------------------------------


class TestNoCostColumn:
    """No cost column at all — profit/margin metrics must be gracefully skipped."""

    def test_date_detected(self, no_cost_df: pd.DataFrame) -> None:
        result = detect_column_roles(no_cost_df, "salon")
        assert result["role_mapping"]["date_column"] == "Transaction Date"

    def test_amount_detected(self, no_cost_df: pd.DataFrame) -> None:
        result = detect_column_roles(no_cost_df, "salon")
        assert result["role_mapping"]["amount_column"] == "Revenue"

    def test_customer_id_detected(self, no_cost_df: pd.DataFrame) -> None:
        result = detect_column_roles(no_cost_df, "salon")
        # 'Customer ID' should map to id_column (high-cardinality text/code)
        assert result["role_mapping"]["id_column"] == "Customer ID"

    def test_cost_column_absent(self, no_cost_df: pd.DataFrame) -> None:
        result = detect_column_roles(no_cost_df, "salon")
        assert result["role_mapping"]["cost_column"] is None

    def test_dashboard_viable_without_cost(self, no_cost_df: pd.DataFrame) -> None:
        result = profile_dataframe(no_cost_df, business_type="salon")
        assert result["dashboard_viable"] is True, (
            f"Dashboard should be viable without a cost column. Error: {result['dashboard_error']}"
        )

    def test_revenue_still_computed(self, no_cost_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(no_cost_df, "salon")
        clean = clean_dataframe(no_cost_df, role_mapping=role_result["role_mapping"])
        metrics = compute_metrics(
            clean["cleaned_df"], "salon", auto_role_mapping=role_result["role_mapping"]
        )
        assert metrics["revenue"] is not None
        assert metrics["revenue"] > 0

    def test_profit_skipped_not_crashed(self, no_cost_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(no_cost_df, "salon")
        clean = clean_dataframe(no_cost_df, role_mapping=role_result["role_mapping"])
        metrics = compute_metrics(
            clean["cleaned_df"], "salon", auto_role_mapping=role_result["role_mapping"]
        )
        # Profit should be None (not an exception) and skipped metric logged
        assert metrics["profit"] is None
        assert metrics["profit_margin"] is None
        skipped_keys = {s["metric"] for s in metrics["skipped_metrics"]}
        assert "profit" in skipped_keys
        assert "profit_margin" in skipped_keys

    def test_skipped_metric_message_is_human_readable(self, no_cost_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(no_cost_df, "salon")
        clean = clean_dataframe(no_cost_df, role_mapping=role_result["role_mapping"])
        metrics = compute_metrics(
            clean["cleaned_df"], "salon", auto_role_mapping=role_result["role_mapping"]
        )
        profit_skip = next(
            (s for s in metrics["skipped_metrics"] if s["metric"] == "profit_margin"), None
        )
        assert profit_skip is not None
        assert "Cost" in profit_skip["reason"] or "cost" in profit_skip["reason"], (
            f"Expected a Cost-related message, got: {profit_skip['reason']!r}"
        )

    def test_customer_metrics_work(self, no_cost_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(no_cost_df, "salon")
        clean = clean_dataframe(no_cost_df, role_mapping=role_result["role_mapping"])
        metrics = compute_metrics(
            clean["cleaned_df"], "salon", auto_role_mapping=role_result["role_mapping"]
        )
        assert metrics["customer_count"] is not None
        assert metrics["customer_count"] > 0
        assert "customers" in metrics["available_sections"]

    def test_full_analysis_does_not_crash(self, no_cost_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(no_cost_df, "salon")
        clean = clean_dataframe(no_cost_df, role_mapping=role_result["role_mapping"])
        analysis = run_full_analysis(
            clean["cleaned_df"], "salon", auto_role_mapping=role_result["role_mapping"]
        )
        assert analysis["dashboard_viable"] is True
        assert isinstance(analysis["insights"], list)
        assert len(analysis["insights"]) > 0


# ---------------------------------------------------------------------------
# Fixture 3 — Messy Dates (Booking Date with mixed/bad formats)
# ---------------------------------------------------------------------------


class TestMessyDates:
    """Mixed date formats in same column; some unparseable rows."""

    def test_date_column_still_detected(self, messy_dates_df: pd.DataFrame) -> None:
        result = detect_column_roles(messy_dates_df, "restaurant")
        assert result["role_mapping"]["date_column"] == "Booking Date", (
            f"Expected 'Booking Date' as date_column despite messy formats, "
            f"got {result['role_mapping']['date_column']!r}"
        )

    def test_amount_column_detected(self, messy_dates_df: pd.DataFrame) -> None:
        result = detect_column_roles(messy_dates_df, "restaurant")
        assert result["role_mapping"]["amount_column"] == "Gross Sales"

    def test_cost_column_detected(self, messy_dates_df: pd.DataFrame) -> None:
        result = detect_column_roles(messy_dates_df, "restaurant")
        assert result["role_mapping"]["cost_column"] == "Cost"

    def test_dashboard_viable(self, messy_dates_df: pd.DataFrame) -> None:
        result = profile_dataframe(messy_dates_df, business_type="restaurant")
        assert result["dashboard_viable"] is True, (
            f"Dashboard should be viable even with messy dates. "
            f"Error: {result['dashboard_error']}"
        )

    def test_partial_date_parse_rate(self, messy_dates_df: pd.DataFrame) -> None:
        """At least 50% of dates must parse successfully (messy_dates.csv has ~9/12 good rows)."""
        from app.services.column_roles import _parse_dates_rowwise

        series = messy_dates_df["Booking Date"]
        stats = _parse_dates_rowwise(series)
        assert stats["parse_rate"] >= 0.5, (
            f"Expected parse_rate >= 0.5 for messy dates, got {stats['parse_rate']}"
        )

    def test_unparseable_dates_flagged_not_crashed(self, messy_dates_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(messy_dates_df, "restaurant")
        clean = clean_dataframe(messy_dates_df, role_mapping=role_result["role_mapping"])
        summary = clean["summary"]
        # There should be some parse failures (the 'not-a-date' row and the blank row)
        # but the pipeline must not crash
        assert "date_parse_failures" in summary
        # Failures are flagged in remaining_issues
        if summary["date_parse_failures"] > 0:
            issues = " ".join(summary.get("remaining_issues", []))
            assert "date" in issues.lower() or "Booking Date" in issues, (
                "Expected a date-related issue to be reported in remaining_issues"
            )

    def test_cleaning_pipeline_log_mentions_date_failures(
        self, messy_dates_df: pd.DataFrame
    ) -> None:
        role_result = detect_column_roles(messy_dates_df, "restaurant")
        clean = clean_dataframe(messy_dates_df, role_mapping=role_result["role_mapping"])
        if clean["summary"]["date_parse_failures"] > 0:
            log_messages = [e["message"] for e in clean["summary"]["pipeline_log"]]
            assert any("unparseable" in m.lower() or "date" in m.lower() for m in log_messages), (
                f"Expected a date warning in the pipeline log. Got: {log_messages}"
            )

    def test_revenue_computed_despite_messy_dates(self, messy_dates_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(messy_dates_df, "restaurant")
        clean = clean_dataframe(messy_dates_df, role_mapping=role_result["role_mapping"])
        metrics = compute_metrics(
            clean["cleaned_df"], "restaurant", auto_role_mapping=role_result["role_mapping"]
        )
        assert metrics["revenue"] is not None
        assert metrics["revenue"] > 0

    def test_profit_computed_with_cost(self, messy_dates_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(messy_dates_df, "restaurant")
        clean = clean_dataframe(messy_dates_df, role_mapping=role_result["role_mapping"])
        metrics = compute_metrics(
            clean["cleaned_df"], "restaurant", auto_role_mapping=role_result["role_mapping"]
        )
        assert metrics["profit"] is not None
        assert metrics["profit_margin"] is not None
        assert "profit" in metrics["available_sections"]

    def test_full_analysis_does_not_crash(self, messy_dates_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(messy_dates_df, "restaurant")
        clean = clean_dataframe(messy_dates_df, role_mapping=role_result["role_mapping"])
        analysis = run_full_analysis(
            clean["cleaned_df"], "restaurant", auto_role_mapping=role_result["role_mapping"]
        )
        assert analysis["dashboard_viable"] is True
        assert isinstance(analysis["insights"], list)


# ---------------------------------------------------------------------------
# Minimum Viable Dashboard — no date AND no amount
# ---------------------------------------------------------------------------


class TestMinimumViableDashboard:
    """Verify the minimum viable dashboard check and error message."""

    def test_no_date_no_amount_returns_clear_error(self) -> None:
        df = pd.DataFrame({
            "Notes": ["foo", "bar", "baz"],
            "Reference": ["A1", "B2", "C3"],
        })
        result = profile_dataframe(df, business_type="other")
        assert result["dashboard_viable"] is False
        assert result["dashboard_error"] is not None
        error = result["dashboard_error"].lower()
        assert "date" in error or "amount" in error or "sales" in error, (
            f"Error should mention missing date/amount, got: {result['dashboard_error']!r}"
        )

    def test_no_date_column_returns_specific_error(self) -> None:
        df = pd.DataFrame({
            "Revenue": [100.0, 200.0, 150.0],
            "Product": ["A", "B", "A"],
        })
        result = profile_dataframe(df, business_type="other")
        assert result["dashboard_viable"] is False
        assert "date" in (result["dashboard_error"] or "").lower()

    def test_no_amount_column_returns_specific_error(self) -> None:
        df = pd.DataFrame({
            "Date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "Notes": ["sold stuff", "more stuff", "even more"],
        })
        result = profile_dataframe(df, business_type="other")
        assert result["dashboard_viable"] is False
        assert result["dashboard_error"] is not None

    def test_dashboard_not_blank_with_viable_check(self) -> None:
        """A viable dataset must have at least revenue in available_sections."""
        df = pd.DataFrame({
            "Date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "Revenue": [100.0, 200.0, 150.0],
        })
        role_result = detect_column_roles(df, "other")
        metrics = compute_metrics(df, "other", auto_role_mapping=role_result["role_mapping"])
        assert metrics["dashboard_viable"] is True
        assert "revenue" in metrics["available_sections"]


# ---------------------------------------------------------------------------
# suggest_ui_confirmations
# ---------------------------------------------------------------------------


class TestUiConfirmations:
    """Verify that suggest_ui_confirmations produces sensible prompts."""

    def test_returns_list(self, alt_headers_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(alt_headers_df, "retail")
        confirmations = suggest_ui_confirmations(
            role_result["role_mapping"], role_result["columns"]
        )
        assert isinstance(confirmations, list)

    def test_confirmation_has_required_keys(self, alt_headers_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(alt_headers_df, "retail")
        confirmations = suggest_ui_confirmations(
            role_result["role_mapping"],
            role_result["columns"],
            confidence_threshold=1.0,  # Force all to trigger
        )
        for c in confirmations:
            assert "role" in c
            assert "column" in c
            assert "confidence" in c
            assert "message" in c
            assert "\u2014" in c["message"] or "confidence" in c["message"].lower()

    def test_message_mentions_column_name(self, no_cost_df: pd.DataFrame) -> None:
        role_result = detect_column_roles(no_cost_df, "salon")
        confirmations = suggest_ui_confirmations(
            role_result["role_mapping"],
            role_result["columns"],
            confidence_threshold=1.0,
        )
        for c in confirmations:
            assert c["column"] in c["message"], (
                f"Expected column name '{c['column']}' in message: {c['message']!r}"
            )

    def test_high_confidence_not_flagged_by_default(self) -> None:
        """A column that scores ~1.0 should NOT appear in confirmations at default threshold."""
        df = pd.DataFrame({"Date": pd.date_range("2024-01-01", periods=20)})
        role_result = detect_column_roles(df, "other")
        confirmations = suggest_ui_confirmations(
            role_result["role_mapping"], role_result["columns"]
        )
        # date_column from a native datetime series should be high-confidence — no prompt
        date_confirmations = [c for c in confirmations if c["role"] == "date_column"]
        for dc in date_confirmations:
            # If it does appear, confidence must be genuinely below threshold
            assert dc["confidence"] < 0.90, (
                f"High-confidence date should not be in confirmations: {dc}"
            )
