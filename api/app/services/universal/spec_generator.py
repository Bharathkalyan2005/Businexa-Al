"""
Stage 2 — LLM Dashboard Specification Generator
================================================
Sends ONLY the Stage 1 profile (never raw data) to an LLM and gets back
a validated JSON spec describing the dashboard to render.

Rules enforced here:
  - LLM is never sent the full dataset, only the structured profile summary
  - LLM must return a strict JSON spec (validated against DashboardSpec schema)
  - Any referenced column/stat must actually exist in the Stage 1 profile
  - On validation failure → one retry with the error message embedded
  - On second failure → deterministic fallback dashboard (row count + summary)
  - Accent color is chosen based on the domain guess, applied consistently
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ValidationError, field_validator, model_validator

from app.config import settings

logger = logging.getLogger(__name__)

# ── Chart type enum (fixed set the frontend knows how to render) ─────────────
ChartType = Literal[
    "bar",
    "line",
    "combo_bar_line",
    "stacked_area",
    "donut",
    "horizontal_bar",
    "scatter",
]

# ── KPI stat reference syntax (validated separately) ─────────────────────────
# Valid patterns:
#   "mean:ColumnName"     → precomputed mean from numeric stats
#   "median:ColumnName"   → precomputed median
#   "min:ColumnName"
#   "max:ColumnName"
#   "std:ColumnName"
#   "outlier_count:ColumnName"
#   "null_pct:ColumnName"
#   "unique_count:ColumnName"  → categorical column
#   "true_pct:ColumnName"      → boolean column
#   "count_where:Col=Value"   → row count where categorical column == value
#   "row_count"               → total dataset rows
#   "col_count"               → total number of columns
_VALID_KPI_STAT_PREFIXES = {
    "mean", "median", "min", "max", "std", "outlier_count",
    "null_pct", "unique_count", "true_pct", "count_where", "span_days",
}
_SIMPLE_KPI_STATS = {"row_count", "col_count"}


# ── Pydantic models ──────────────────────────────────────────────────────────

class KpiCard(BaseModel):
    title: str
    stat_ref: str          # e.g. "mean:Revenue", "row_count"
    format: str = "number" # "number" | "percent" | "currency" | "date"
    icon: str = "chart"    # icon hint for the renderer

    @field_validator("stat_ref")
    @classmethod
    def _validate_stat_ref(cls, v: str) -> str:
        if v in _SIMPLE_KPI_STATS:
            return v
        parts = v.split(":", 1)
        if len(parts) != 2 or parts[0] not in _VALID_KPI_STAT_PREFIXES:
            raise ValueError(
                f"Invalid stat_ref '{v}'. Must be one of {_SIMPLE_KPI_STATS} "
                f"or '<prefix>:<column>' where prefix is one of {_VALID_KPI_STAT_PREFIXES}."
            )
        return v


class ChartSpec(BaseModel):
    title: str
    chart_type: ChartType
    x_column: str                         # column used for X axis / grouping
    y_columns: list[str]                  # columns used for Y axis values
    aggregate: str = "mean"               # how y_columns are aggregated
    description: str = ""                 # optional tooltip description


class DashboardSpec(BaseModel):
    domain: str                           # guessed domain, e.g. "E-commerce Sales"
    title: str                            # dashboard title
    accent_color: str                     # CSS hex or named color
    kpi_cards: list[KpiCard]
    charts: list[ChartSpec]

    @field_validator("kpi_cards")
    @classmethod
    def _four_kpis(cls, v: list[KpiCard]) -> list[KpiCard]:
        if len(v) != 4:
            raise ValueError(f"Must have exactly 4 KPI cards, got {len(v)}")
        return v

    @field_validator("charts")
    @classmethod
    def _charts_range(cls, v: list[ChartSpec]) -> list[ChartSpec]:
        if not (4 <= len(v) <= 6):
            raise ValueError(f"Must have 4–6 charts, got {len(v)}")
        return v

    @model_validator(mode="after")
    def _no_repeated_chart_types(self) -> "DashboardSpec":
        types = [c.chart_type for c in self.charts]
        if len(types) != len(set(types)):
            # Deduplicate but don't hard-fail — just warn
            logger.warning("LLM returned repeated chart types: %s", types)
        return self


# ── Profile → compact prompt payload ─────────────────────────────────────────

def _build_profile_summary(profile: dict[str, Any]) -> str:
    """Convert the Stage 1 profile into a compact text summary for the LLM prompt.
    This is all the LLM ever sees — no raw data."""
    lines: list[str] = []
    lines.append(f"DATASET SUMMARY")
    lines.append(f"Rows: {profile['row_count']}  Columns: {profile['col_count']}")
    lines.append(f"Detected target/outcome column: {profile.get('target_column') or 'none'}")
    lines.append("")

    lines.append("COLUMN PROFILES:")
    for cp in profile.get("columns", []):
        col = cp["column"]
        t = cp["type"]
        null = cp["null_pct"]
        s = cp.get("stats", {})

        if t == "numeric":
            lines.append(
                f"  [{t}] {col}  null%={null:.1f}"
                f"  min={s.get('min')}  max={s.get('max')}"
                f"  mean={s.get('mean'):.3f}  median={s.get('median'):.3f}"
                f"  std={s.get('std'):.3f}  outliers={s.get('outlier_count')}"
            )
        elif t == "categorical":
            top = ", ".join(
                f"{tv['value']}({tv['pct']}%)"
                for tv in s.get("top_values", [])[:5]
            )
            lines.append(
                f"  [{t}] {col}  null%={null:.1f}"
                f"  unique={s.get('unique_count')}  top_values=[{top}]"
            )
        elif t == "datetime":
            lines.append(
                f"  [{t}] {col}  null%={null:.1f}"
                f"  range=[{s.get('min', '')[:10]}..{s.get('max', '')[:10]}]"
                f"  granularity={s.get('granularity')}"
            )
        elif t == "boolean":
            lines.append(
                f"  [{t}] {col}  null%={null:.1f}"
                f"  true%={s.get('true_pct')}  true={s.get('true_count')}  false={s.get('false_count')}"
            )
        else:
            lines.append(f"  [{t}] {col}  null%={null:.1f}  unique={s.get('unique_count')}")

    if profile.get("correlation_matrix"):
        lines.append("")
        lines.append("CORRELATION MATRIX (Pearson, numeric columns only):")
        corr = profile["correlation_matrix"]
        cols = list(corr.keys())
        for c1 in cols:
            row_parts = []
            for c2 in cols:
                if c1 != c2:
                    val = corr[c1].get(c2)
                    if val is not None:
                        row_parts.append(f"{c2}={val:.3f}")
            if row_parts:
                lines.append(f"  {c1}: {', '.join(row_parts)}")

    if profile.get("groupby_aggregates"):
        lines.append("")
        lines.append("GROUP-BY AGGREGATES (categorical × numeric, mean/count per group):")
        for cat_col, num_dict in list(profile["groupby_aggregates"].items())[:4]:
            for num_col, rows in list(num_dict.items())[:3]:
                group_summary = ", ".join(
                    f"{r['group']}→mean={r['mean']:.2f}(n={r['count']})"
                    for r in rows[:5]
                )
                lines.append(f"  {cat_col} × {num_col}: {group_summary}")

    if profile.get("sample_rows"):
        lines.append("")
        lines.append("SAMPLE ROWS (first 5):")
        for row in profile["sample_rows"][:5]:
            lines.append(f"  {json.dumps(row)}")

    return "\n".join(lines)


_SYSTEM_PROMPT = """You are a senior data analyst and dashboard designer.
You will receive a structured statistical profile of a dataset (never the raw data).
Your job is to return a JSON dashboard specification — NOTHING ELSE, no prose, no markdown fences.

STRICT RULES:
1. Return ONLY valid JSON — no markdown, no explanation text.
2. stat_ref values in kpi_cards MUST use ONLY precomputed stats from the profile.
   Valid formats:
     "row_count"                    — total row count
     "col_count"                    — total column count
     "mean:<ColumnName>"            — mean of a numeric column
     "median:<ColumnName>"          — median of a numeric column
     "min:<ColumnName>"             — min of a numeric column
     "max:<ColumnName>"             — max of a numeric column
     "std:<ColumnName>"             — std of a numeric column
     "null_pct:<ColumnName>"        — null percentage of any column
     "unique_count:<ColumnName>"    — unique count of a categorical column
     "true_pct:<ColumnName>"        — true% of a boolean column
     "count_where:<Col>=<Value>"    — count of rows where categorical equals value
     "span_days:<ColumnName>"       — date span in days of a datetime column
   NEVER invent numerical values. The renderer fetches the actual value from the profile.
3. x_column and y_columns in charts MUST be actual column names from the profile.
4. Use exactly 4 kpi_cards and between 4 and 6 charts.
5. Deliberately use DIFFERENT chart types — no more than one chart of any type.
6. Choose ONE accent_color (hex) that fits the domain:
   - Health/clinical → "#e11d48" (red-rose)
   - Finance/business/sales → "#0ea5e9" (sky-blue)
   - HR/people → "#8b5cf6" (violet)
   - Sports/fitness → "#f97316" (orange)
   - Education → "#10b981" (emerald)
   - Other → "#6366f1" (indigo)

Return exactly this JSON shape:
{
  "domain": "string",
  "title": "string",
  "accent_color": "#hexcode",
  "kpi_cards": [
    { "title": "string", "stat_ref": "string", "format": "number|percent|currency|date", "icon": "string" },
    ...4 total...
  ],
  "charts": [
    {
      "title": "string",
      "chart_type": "bar|line|combo_bar_line|stacked_area|donut|horizontal_bar|scatter",
      "x_column": "string",
      "y_columns": ["string"],
      "aggregate": "mean|count|sum",
      "description": "string"
    },
    ...4-6 total, all different chart_type values...
  ]
}"""

_USER_PROMPT_TEMPLATE = """Below is the Stage 1 statistical profile of an uploaded dataset.
Analyze it and return the dashboard specification JSON.

{profile_summary}

Remember: return ONLY the JSON object, no other text."""


# ── Column/stat validation against the profile ────────────────────────────────

def _resolve_kpi_value(stat_ref: str, profile: dict[str, Any]) -> float | int | str | None:
    """Resolve a stat_ref to its actual value from the profile. Returns None if not found."""
    if stat_ref == "row_count":
        return profile.get("row_count")
    if stat_ref == "col_count":
        return profile.get("col_count")

    col_map: dict[str, dict[str, Any]] = {
        cp["column"]: cp for cp in profile.get("columns", [])
    }

    if ":" not in stat_ref:
        return None

    prefix, rest = stat_ref.split(":", 1)

    if prefix == "count_where":
        # "count_where:Col=Value"
        if "=" not in rest:
            return None
        col, val = rest.split("=", 1)
        col_profile = col_map.get(col)
        if not col_profile:
            return None
        top_vals = col_profile.get("stats", {}).get("top_values", [])
        for tv in top_vals:
            if tv["value"] == val:
                return tv["count"]
        return 0

    col_profile = col_map.get(rest)
    if not col_profile:
        return None

    stats = col_profile.get("stats", {})
    return stats.get(prefix)


def _validate_spec_against_profile(
    spec: DashboardSpec,
    profile: dict[str, Any],
) -> list[str]:
    """Return a list of validation errors. Empty list = all good."""
    errors: list[str] = []
    col_names = {cp["column"] for cp in profile.get("columns", [])}

    for i, kpi in enumerate(spec.kpi_cards):
        val = _resolve_kpi_value(kpi.stat_ref, profile)
        if val is None:
            errors.append(
                f"KPI[{i}] stat_ref '{kpi.stat_ref}' does not resolve to any value "
                f"in the Stage 1 profile."
            )

    for i, chart in enumerate(spec.charts):
        if chart.x_column not in col_names:
            errors.append(
                f"Chart[{i}] x_column '{chart.x_column}' is not a column in the profile. "
                f"Available: {sorted(col_names)}"
            )
        for y in chart.y_columns:
            if y not in col_names:
                errors.append(
                    f"Chart[{i}] y_column '{y}' is not a column in the profile. "
                    f"Available: {sorted(col_names)}"
                )

    return errors


# ── Fallback dashboard ────────────────────────────────────────────────────────

def _fallback_dashboard(profile: dict[str, Any]) -> DashboardSpec:
    """Generate a safe, minimal dashboard when LLM spec is invalid."""
    numeric_cols = profile.get("numeric_columns", [])
    cat_cols = profile.get("categorical_columns", [])
    datetime_cols = profile.get("datetime_columns", [])

    kpis: list[dict[str, Any]] = [{"title": "Total Rows", "stat_ref": "row_count", "format": "number", "icon": "table"}]

    if numeric_cols:
        kpis.append({"title": f"Avg {numeric_cols[0]}", "stat_ref": f"mean:{numeric_cols[0]}", "format": "number", "icon": "trending-up"})
    else:
        kpis.append({"title": "Columns", "stat_ref": "col_count", "format": "number", "icon": "columns"})

    if len(numeric_cols) >= 2:
        kpis.append({"title": f"Max {numeric_cols[1]}", "stat_ref": f"max:{numeric_cols[1]}", "format": "number", "icon": "arrow-up"})
    elif cat_cols:
        kpis.append({"title": f"{cat_cols[0]} Unique Values", "stat_ref": f"unique_count:{cat_cols[0]}", "format": "number", "icon": "tag"})
    else:
        kpis.append({"title": "Columns", "stat_ref": "col_count", "format": "number", "icon": "columns"})

    if numeric_cols:
        kpis.append({"title": f"Median {numeric_cols[0]}", "stat_ref": f"median:{numeric_cols[0]}", "format": "number", "icon": "activity"})
    else:
        kpis.append({"title": "Total Rows", "stat_ref": "row_count", "format": "number", "icon": "table"})

    charts: list[dict[str, Any]] = []
    if cat_cols and numeric_cols:
        charts.append({
            "title": f"{numeric_cols[0]} by {cat_cols[0]}",
            "chart_type": "bar",
            "x_column": cat_cols[0],
            "y_columns": [numeric_cols[0]],
            "aggregate": "mean",
            "description": "Average value by category",
        })
    if datetime_cols and numeric_cols:
        charts.append({
            "title": f"{numeric_cols[0]} Over Time",
            "chart_type": "line",
            "x_column": datetime_cols[0],
            "y_columns": [numeric_cols[0]],
            "aggregate": "mean",
            "description": "Trend over time",
        })
    if len(numeric_cols) >= 2:
        charts.append({
            "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
            "chart_type": "scatter",
            "x_column": numeric_cols[0],
            "y_columns": [numeric_cols[1]],
            "aggregate": "mean",
            "description": "Relationship between two numeric columns",
        })
    if cat_cols:
        charts.append({
            "title": f"{cat_cols[0]} Distribution",
            "chart_type": "donut",
            "x_column": cat_cols[0],
            "y_columns": [cat_cols[0]],
            "aggregate": "count",
            "description": "Distribution of categories",
        })

    # Pad to at least 4
    while len(charts) < 4 and numeric_cols:
        idx = len(charts)
        c_types: list[ChartType] = ["horizontal_bar", "stacked_area"]
        col = numeric_cols[min(idx, len(numeric_cols) - 1)]
        gcat = cat_cols[0] if cat_cols else col
        charts.append({
            "title": f"Breakdown: {col}",
            "chart_type": c_types[idx % len(c_types)],
            "x_column": gcat,
            "y_columns": [col],
            "aggregate": "mean",
            "description": "Value breakdown",
        })

    return DashboardSpec(
        domain="General",
        title="Dataset Summary Dashboard",
        accent_color="#6366f1",
        kpi_cards=[KpiCard(**k) for k in kpis[:4]],
        charts=[ChartSpec(**c) for c in charts[:6]],
    )


# ── Claude API caller ─────────────────────────────────────────────────────────

async def _call_groq(prompt: str) -> str:
    """Call Groq chat-completions API (OpenAI-compatible) for dashboard spec.

    Tries models in priority order — first available wins.
    Models confirmed available on the free/dev tier as of 2026-09:
      openai/gpt-oss-120b   — 120B, best quality
      qwen/qwen3.8-27b      — 27B Qwen3, fast fallback
    """
    api_key = settings.groq_api_key
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set in environment. "
            "Add it to api/.env as GROQ_API_KEY=gsk_..."
        )

    _MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]

    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=45.0) as client:
        for model in _MODELS:
            try:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "temperature": 0.2,
                        "max_tokens": 2048,
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {"role": "user",   "content": prompt},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info("Groq model '%s' responded successfully.", model)
                return data["choices"][0]["message"]["content"]
            except Exception as exc:
                logger.warning("Groq model '%s' failed: %s", model, exc)
                last_exc = exc

    raise last_exc or RuntimeError("All Groq models failed.")


def _parse_spec(raw: str) -> DashboardSpec:
    """Extract JSON from LLM response and parse into DashboardSpec.

    Groq with response_format=json_object returns pure JSON, so we only
    need to strip markdown fences as a safety net.
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()
    payload = json.loads(text)
    return DashboardSpec.model_validate(payload)


# ── Main public function ──────────────────────────────────────────────────────

async def generate_dashboard_spec(
    profile: dict[str, Any],
) -> tuple[DashboardSpec, bool]:
    """
    Stage 2: Send profile to Claude, validate the returned spec.

    Returns
    -------
    (spec, used_fallback) where used_fallback=True if LLM failed.
    """
    profile_summary = _build_profile_summary(profile)
    user_prompt = _USER_PROMPT_TEMPLATE.format(profile_summary=profile_summary)

    for attempt in (1, 2):
        try:
            raw = await _call_groq(user_prompt)
        except Exception as exc:
            logger.error("Groq API call failed (attempt %d): %s", attempt, exc)
            break

        try:
            spec = _parse_spec(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("LLM returned invalid JSON/schema (attempt %d): %s", attempt, exc)
            if attempt == 1:
                # Embed the error into the next prompt
                user_prompt = (
                    user_prompt
                    + f"\n\nYour previous response had this error: {exc}\n"
                    "Fix it and return ONLY valid JSON this time."
                )
            continue

        profile_errors = _validate_spec_against_profile(spec, profile)
        if profile_errors:
            err_msg = "\n".join(profile_errors)
            logger.warning("Spec failed profile validation (attempt %d):\n%s", attempt, err_msg)
            if attempt == 1:
                user_prompt = (
                    user_prompt
                    + f"\n\nYour previous response referenced columns/stats that don't exist:\n{err_msg}\n"
                    "Fix it and return ONLY valid JSON."
                )
            continue

        logger.info("Dashboard spec generated successfully (attempt %d)", attempt)
        return spec, False

    # Both attempts failed → fallback
    logger.warning("Using fallback dashboard spec after LLM failure.")
    return _fallback_dashboard(profile), True


def resolve_all_kpi_values(
    spec: DashboardSpec,
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Resolve every KPI stat_ref to its actual value from the Stage 1 profile.
    Returns a list of {title, value, format, icon} dicts ready for the frontend.
    """
    result = []
    for kpi in spec.kpi_cards:
        val = _resolve_kpi_value(kpi.stat_ref, profile)
        result.append({
            "title": kpi.title,
            "stat_ref": kpi.stat_ref,
            "value": val,
            "format": kpi.format,
            "icon": kpi.icon,
        })
    return result
