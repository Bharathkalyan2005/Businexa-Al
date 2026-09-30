"use client";

import React from "react";
import type { KpiCard } from "@/lib/types/universal-dashboard";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Users,
  BarChart2,
  Layers,
  Tag,
  Calendar,
  ArrowUp,
  ArrowDown,
  Table2,
  Hash,
  Percent,
  DollarSign,
} from "lucide-react";

const ICON_MAP: Record<string, React.ElementType> = {
  "trending-up": TrendingUp,
  "trending-down": TrendingDown,
  activity: Activity,
  users: Users,
  chart: BarChart2,
  layers: Layers,
  tag: Tag,
  calendar: Calendar,
  "arrow-up": ArrowUp,
  "arrow-down": ArrowDown,
  table: Table2,
  columns: Layers,
  hash: Hash,
  percent: Percent,
  currency: DollarSign,
};

function formatValue(value: number | string | null, format: string): string {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (isNaN(num)) return String(value);

  switch (format) {
    case "currency":
      return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(num);
    case "percent":
      return `${num.toFixed(1)}%`;
    case "date":
      return String(value);
    default:
      if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M`;
      if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
      return num % 1 === 0 ? num.toLocaleString() : num.toFixed(2);
  }
}

interface KpiCardProps {
  card: KpiCard;
  accent: string;
}

export function KpiCardComponent({ card, accent }: KpiCardProps) {
  const IconComp = ICON_MAP[card.icon] ?? BarChart2;
  const displayValue = formatValue(card.value, card.format);

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-sm transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
      {/* Subtle accent gradient top bar */}
      <div
        className="absolute inset-x-0 top-0 h-0.5 opacity-80"
        style={{ background: `linear-gradient(90deg, ${accent}, transparent)` }}
      />
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground truncate">
            {card.title}
          </p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-foreground" title={String(card.value ?? "")}>
            {displayValue}
          </p>
        </div>
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ml-3"
          style={{ backgroundColor: `${accent}18` }}
        >
          <IconComp className="h-5 w-5" style={{ color: accent }} strokeWidth={1.8} />
        </div>
      </div>
    </div>
  );
}

interface KpiRowProps {
  cards: KpiCard[];
  accent: string;
}

export function KpiRow({ cards, accent }: KpiRowProps) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((card, i) => (
        <KpiCardComponent key={i} card={card} accent={accent} />
      ))}
    </div>
  );
}
