"use client";

/**
 * Fixed library of chart renderer components for the Universal Dashboard.
 * Each component reads pre-computed data from the Stage 1 profile —
 * nothing is computed here; we only transform profile data into Recharts format.
 *
 * Supported chart types:
 *   bar | line | combo_bar_line | stacked_area | donut | horizontal_bar | scatter
 */

import React from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  ComposedChart,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { ChartSpec, DataProfile } from "@/lib/types/universal-dashboard";

// ── Colour utilities ──────────────────────────────────────────────────────────

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

function buildPalette(accent: string, n: number): string[] {
  const [r, g, b] = hexToRgb(accent);
  return Array.from({ length: n }, (_, i) => {
    const t = i / Math.max(n - 1, 1);
    const mix = (channel: number) =>
      Math.round(channel * (1 - t * 0.55) + 255 * t * 0.1);
    return `rgb(${mix(r)},${mix(g)},${mix(b)})`;
  });
}

// ── Data extraction helpers ───────────────────────────────────────────────────

type GroupRow = { group: string; mean: number | null; count: number };

/** Extract group-by rows from the profile for a given cat × num pair. */
function getGroupByData(
  profile: DataProfile,
  catCol: string,
  numCol: string,
): { name: string; value: number }[] {
  const rows: GroupRow[] | undefined =
    profile.groupby_aggregates?.[catCol]?.[numCol];
  if (!rows) return [];
  return rows
    .filter((r) => r.mean !== null)
    .map((r) => ({ name: r.group, value: Number((r.mean ?? 0).toFixed(2)) }));
}

/** Get top-5 frequency data for a categorical column. */
function getCategoricalData(
  profile: DataProfile,
  col: string,
): { name: string; value: number }[] {
  const cp = profile.columns.find((c) => c.column === col);
  if (!cp || cp.type !== "categorical") return [];
  const top = (cp.stats as { top_values?: { value: string; count: number }[] })
    ?.top_values;
  return (top ?? []).map((tv) => ({ name: tv.value, value: tv.count }));
}

/** Build scatter data from two numeric columns using sample rows. */
function getScatterData(
  profile: DataProfile,
  xCol: string,
  yCol: string,
): { x: number; y: number }[] {
  return profile.sample_rows
    .map((row) => ({
      x: Number(row[xCol]),
      y: Number(row[yCol]),
    }))
    .filter((d) => !isNaN(d.x) && !isNaN(d.y));
}

/** Extract data for any chart — tries groupby, falls back to categorical counts. */
function extractChartData(
  profile: DataProfile,
  spec: ChartSpec,
): Record<string, unknown>[] {
  const { x_column, y_columns } = spec;

  if (spec.chart_type === "scatter") {
    return getScatterData(profile, x_column, y_columns[0] ?? x_column) as unknown as Record<string, unknown>[];
  }

  // Try group-by aggregates first (cat × numeric)
  if (y_columns.length > 0) {
    const rows = getGroupByData(profile, x_column, y_columns[0]);
    if (rows.length > 0) {
      if (y_columns.length === 1) return rows as unknown as Record<string, unknown>[];
      // Multi-column: merge additional y_columns from other groupby entries
      const merged: Record<string, Record<string, number>> = {};
      for (const r of rows) merged[r.name] = { [y_columns[0]]: r.value };
      for (const yCol of y_columns.slice(1)) {
        const extra = getGroupByData(profile, x_column, yCol);
        for (const r of extra) {
          if (!merged[r.name]) merged[r.name] = {};
          merged[r.name][yCol] = r.value;
        }
      }
      return Object.entries(merged).map(([name, vals]) => ({ name, ...vals }));
    }
  }

  // Fall back to top-value frequency for the x_column
  return getCategoricalData(profile, x_column) as unknown as Record<string, unknown>[];
}

// ── Tooltip formatter ─────────────────────────────────────────────────────────

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-card/95 px-3 py-2 shadow-lg backdrop-blur-sm text-sm">
      {label && <p className="font-medium text-foreground mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="text-xs">
          {p.name}: <span className="font-semibold">{typeof p.value === "number" ? p.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : p.value}</span>
        </p>
      ))}
    </div>
  );
};

// ── Individual chart renderers ────────────────────────────────────────────────

interface ChartRendererProps {
  spec: ChartSpec;
  profile: DataProfile;
  accent: string;
}

function BarChartRenderer({ spec, profile, accent }: ChartRendererProps) {
  const data = extractChartData(profile, spec);
  const palette = buildPalette(accent, spec.y_columns.length || 1);
  const yKeys = spec.y_columns.length > 0 ? spec.y_columns : ["value"];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={50} />
        <Tooltip content={<CustomTooltip />} />
        {yKeys.length > 1 && <Legend />}
        {yKeys.map((key, i) => (
          <Bar key={key} dataKey={key === spec.y_columns[0] ? "value" : key} fill={palette[i]} radius={[4, 4, 0, 0]} name={key} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function LineChartRenderer({ spec, profile, accent }: ChartRendererProps) {
  const data = extractChartData(profile, spec);
  const palette = buildPalette(accent, spec.y_columns.length || 1);
  const yKeys = spec.y_columns.length > 0 ? spec.y_columns : ["value"];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={50} />
        <Tooltip content={<CustomTooltip />} />
        {yKeys.length > 1 && <Legend />}
        {yKeys.map((key, i) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key === spec.y_columns[0] ? "value" : key}
            stroke={palette[i]}
            strokeWidth={2.5}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            name={key}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function ComboBarLineRenderer({ spec, profile, accent }: ChartRendererProps) {
  const data = extractChartData(profile, spec);
  const [r, g, b] = hexToRgb(accent);
  const barColor = accent;
  const lineColor = `rgb(${Math.round(r * 0.5)},${Math.round(g * 0.5 + 128)},${Math.round(b * 0.7 + 80)})`;
  const yKeys = spec.y_columns.length > 0 ? spec.y_columns : ["value"];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={50} />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Bar dataKey={yKeys[0] === spec.y_columns[0] ? "value" : yKeys[0]} fill={barColor} radius={[4, 4, 0, 0]} name={yKeys[0]} />
        {yKeys[1] && (
          <Line type="monotone" dataKey={yKeys[1]} stroke={lineColor} strokeWidth={2.5} dot={{ r: 3 }} name={yKeys[1]} />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function StackedAreaRenderer({ spec, profile, accent }: ChartRendererProps) {
  const data = extractChartData(profile, spec);
  const palette = buildPalette(accent, Math.max(spec.y_columns.length, 1));
  const yKeys = spec.y_columns.length > 0 ? spec.y_columns : ["value"];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <defs>
          {yKeys.map((key, i) => (
            <linearGradient key={key} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={palette[i]} stopOpacity={0.4} />
              <stop offset="95%" stopColor={palette[i]} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={50} />
        <Tooltip content={<CustomTooltip />} />
        {yKeys.length > 1 && <Legend />}
        {yKeys.map((key, i) => (
          <Area
            key={key}
            type="monotone"
            dataKey={i === 0 ? "value" : key}
            stroke={palette[i]}
            strokeWidth={2.5}
            fill={`url(#grad-${i})`}
            name={key}
            stackId="1"
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

function DonutRenderer({ spec, profile, accent }: ChartRendererProps) {
  const data = getCategoricalData(profile, spec.x_column);
  const palette = buildPalette(accent, data.length || 1);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={65}
          outerRadius={100}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((_, i) => (
            <Cell key={i} fill={palette[i % palette.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          formatter={(value: string) => <span className="text-xs">{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

function HorizontalBarRenderer({ spec, profile, accent }: ChartRendererProps) {
  const data = extractChartData(profile, spec);
  const palette = buildPalette(accent, 1);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 24, left: 60, bottom: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={56} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="value" fill={palette[0]} radius={[0, 4, 4, 0]} name={spec.y_columns[0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function ScatterRenderer({ spec, profile, accent }: ChartRendererProps) {
  const data = getScatterData(profile, spec.x_column, spec.y_columns[0] ?? spec.x_column);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
        <XAxis
          dataKey="x"
          name={spec.x_column}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          label={{ value: spec.x_column, position: "insideBottom", offset: -4, fontSize: 11 }}
        />
        <YAxis
          dataKey="y"
          name={spec.y_columns[0]}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={50}
          label={{ value: spec.y_columns[0], angle: -90, position: "insideLeft", fontSize: 11 }}
        />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<CustomTooltip />} />
        <Scatter data={data} fill={accent} fillOpacity={0.7} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

// ── Main export: pick the right renderer ─────────────────────────────────────

export function ChartRenderer({ spec, profile, accent }: ChartRendererProps) {
  switch (spec.chart_type) {
    case "bar":           return <BarChartRenderer spec={spec} profile={profile} accent={accent} />;
    case "line":          return <LineChartRenderer spec={spec} profile={profile} accent={accent} />;
    case "combo_bar_line":return <ComboBarLineRenderer spec={spec} profile={profile} accent={accent} />;
    case "stacked_area":  return <StackedAreaRenderer spec={spec} profile={profile} accent={accent} />;
    case "donut":         return <DonutRenderer spec={spec} profile={profile} accent={accent} />;
    case "horizontal_bar":return <HorizontalBarRenderer spec={spec} profile={profile} accent={accent} />;
    case "scatter":       return <ScatterRenderer spec={spec} profile={profile} accent={accent} />;
    default:              return <BarChartRenderer spec={spec} profile={profile} accent={accent} />;
  }
}
