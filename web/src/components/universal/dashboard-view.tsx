"use client";

import React, { useState } from "react";
import { AlertTriangle, RotateCcw, Info, Layers } from "lucide-react";
import type { UniversalDashboardResponse } from "@/lib/types/universal-dashboard";
import { KpiRow } from "@/components/universal/kpi-cards";
import { ChartRenderer } from "@/components/universal/chart-renderers";

// ── Loading skeleton ──────────────────────────────────────────────────────────

function SkeletonPulse({ className }: { className?: string }) {
  return (
    <div className={["animate-pulse rounded-2xl bg-muted", className].filter(Boolean).join(" ")} />
  );
}

export function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-8 p-6 lg:p-10 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <SkeletonPulse className="h-7 w-56" />
        <SkeletonPulse className="h-4 w-36" />
      </div>
      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => <SkeletonPulse key={i} className="h-28" />)}
      </div>
      {/* Charts */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((i) => <SkeletonPulse key={i} className="h-72" />)}
      </div>
    </div>
  );
}

// ── Degraded mode banner ──────────────────────────────────────────────────────

function DegradedBanner({ reason }: { reason: string | null }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-yellow-400/30 bg-yellow-50/60 px-4 py-3 dark:bg-yellow-900/20">
      <AlertTriangle className="h-5 w-5 shrink-0 text-yellow-600 mt-0.5" />
      <div>
        <p className="text-sm font-semibold text-yellow-700 dark:text-yellow-400">
          Limited data detected
        </p>
        <p className="text-xs text-yellow-600/90 dark:text-yellow-500 mt-0.5">
          {reason ?? "Dataset has too few rows or columns for a full dashboard."}
        </p>
      </div>
    </div>
  );
}

// ── Fallback banner ──────────────────────────────────────────────────────────

function FallbackBanner() {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-blue-400/30 bg-blue-50/60 px-4 py-3 dark:bg-blue-900/20">
      <Info className="h-5 w-5 shrink-0 text-blue-600 mt-0.5" />
      <p className="text-xs text-blue-600/90 dark:text-blue-400">
        AI spec generation encountered an issue — showing auto-generated fallback dashboard.
      </p>
    </div>
  );
}

// ── Chart card wrapper ────────────────────────────────────────────────────────

function ChartCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="group flex flex-col rounded-2xl border border-border bg-card p-5 shadow-sm transition-all duration-200 hover:shadow-md">
      <div className="mb-1">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {description && (
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{description}</p>
        )}
      </div>
      <div className="flex-1 min-h-0 pt-2">{children}</div>
    </div>
  );
}

// ── Main Dashboard view ───────────────────────────────────────────────────────

interface DashboardViewProps {
  data: UniversalDashboardResponse;
  onReset: () => void;
}

export function DashboardView({ data, onReset }: DashboardViewProps) {
  const [showProfile, setShowProfile] = useState(false);

  const {
    profile,
    title,
    domain,
    accent_color,
    kpi_cards,
    charts,
    used_fallback,
    degraded_mode,
  } = data;

  return (
    <div className="flex flex-col gap-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

      {/* ── Top header bar ─────────────────────────────────────────────────── */}
      <div
        className="flex items-start justify-between rounded-2xl border border-border/60 bg-card px-6 py-5 shadow-sm"
        style={{ borderLeftColor: accent_color, borderLeftWidth: 3 }}
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span
              className="inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide uppercase"
              style={{ backgroundColor: `${accent_color}22`, color: accent_color }}
            >
              {domain}
            </span>
            {used_fallback && (
              <span className="text-xs text-muted-foreground italic">(fallback spec)</span>
            )}
          </div>
          <h1 className="text-xl font-bold text-foreground">{title}</h1>
          <p className="text-xs text-muted-foreground mt-1">
            {profile.row_count.toLocaleString()} rows · {profile.col_count} columns
            {profile.target_column && ` · Target: ${profile.target_column}`}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowProfile((p) => !p)}
            className="flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-xs font-medium text-muted-foreground transition hover:bg-muted/60"
          >
            <Layers className="h-3.5 w-3.5" />
            {showProfile ? "Hide" : "Show"} profile
          </button>
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-xs font-medium text-muted-foreground transition hover:bg-muted/60"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            New file
          </button>
        </div>
      </div>

      {/* ── Banners ────────────────────────────────────────────────────────── */}
      {degraded_mode && <DegradedBanner reason={profile.degraded_reason} />}
      {used_fallback && !degraded_mode && <FallbackBanner />}

      {/* ── KPI row ────────────────────────────────────────────────────────── */}
      <KpiRow cards={kpi_cards} accent={accent_color} />

      {/* ── Chart grid ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {charts.map((chart, i) => (
          <ChartCard key={i} title={chart.title} description={chart.description}>
            <ChartRenderer spec={chart} profile={profile} accent={accent_color} />
          </ChartCard>
        ))}
      </div>

      {/* ── Raw profile inspector (collapsible) ────────────────────────────── */}
      {showProfile && (
        <div className="rounded-2xl border border-border bg-muted/30 p-5 animate-in fade-in duration-300">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
            Stage 1 Data Profile
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-semibold">Column</th>
                  <th className="pb-2 pr-4 font-semibold">Type</th>
                  <th className="pb-2 pr-4 font-semibold">Null %</th>
                  <th className="pb-2 font-semibold">Key stats</th>
                </tr>
              </thead>
              <tbody>
                {profile.columns.map((cp) => {
                  const s = cp.stats as Record<string, unknown> | undefined;
                  let statsStr = "";
                  if (cp.type === "numeric" && s) {
                    statsStr = `mean=${(s.mean as number)?.toFixed(2)}  median=${(s.median as number)?.toFixed(2)}  outliers=${s.outlier_count}`;
                  } else if (cp.type === "categorical" && s) {
                    const top = (s.top_values as { value: string; pct: number }[])?.[0];
                    statsStr = `uniq=${s.unique_count}  top: ${top?.value} (${top?.pct}%)`;
                  } else if (cp.type === "datetime" && s) {
                    statsStr = `span=${s.span_days}d  ${s.granularity}`;
                  } else if (cp.type === "boolean" && s) {
                    statsStr = `true%=${s.true_pct}  true=${s.true_count}  false=${s.false_count}`;
                  } else if (s) {
                    statsStr = `uniq=${s.unique_count}`;
                  }
                  const isTarget = cp.column === profile.target_column;
                  return (
                    <tr
                      key={cp.column}
                      className="border-b border-border/50 transition-colors hover:bg-muted/40"
                    >
                      <td className="py-2 pr-4 font-mono font-medium text-foreground">
                        {cp.column}
                        {isTarget && (
                          <span
                            className="ml-2 rounded-full px-1.5 py-0.5 text-[10px] font-bold uppercase"
                            style={{ backgroundColor: `${accent_color}22`, color: accent_color }}
                          >
                            target
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-muted-foreground">{cp.type}</td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        <span className={cp.null_pct > 5 ? "text-yellow-600 font-semibold" : ""}>
                          {cp.null_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-2 font-mono text-muted-foreground">{statsStr}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
