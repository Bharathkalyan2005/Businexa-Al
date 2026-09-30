/**
 * TypeScript types for the Universal Dashboard pipeline.
 * These mirror the Pydantic response models from the FastAPI backend.
 */

export type ChartType =
  | "bar"
  | "line"
  | "combo_bar_line"
  | "stacked_area"
  | "donut"
  | "horizontal_bar"
  | "scatter";

export interface KpiCard {
  title: string;
  stat_ref: string;
  value: number | string | null;
  format: "number" | "percent" | "currency" | "date";
  icon: string;
}

export interface ChartSpec {
  title: string;
  chart_type: ChartType;
  x_column: string;
  y_columns: string[];
  aggregate: string;
  description: string;
}

export interface ColumnProfile {
  column: string;
  type: "numeric" | "categorical" | "datetime" | "boolean" | "free_text" | "id_like";
  null_pct: number;
  stats?: Record<string, unknown>;
}

export interface DataProfile {
  row_count: number;
  col_count: number;
  degraded_mode: boolean;
  degraded_reason: string | null;
  columns: ColumnProfile[];
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  boolean_columns: string[];
  id_like_columns: string[];
  free_text_columns: string[];
  correlation_matrix: Record<string, Record<string, number | null>>;
  groupby_aggregates: Record<
    string,
    Record<string, { group: string; mean: number | null; count: number }[]>
  >;
  target_column: string | null;
  sample_rows: Record<string, unknown>[];
}

export interface UniversalDashboardResponse {
  profile: DataProfile;
  domain: string;
  title: string;
  accent_color: string;
  kpi_cards: KpiCard[];
  charts: ChartSpec[];
  used_fallback: boolean;
  degraded_mode: boolean;
}
