"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface RevenueChartProps {
  data: { date?: string; month?: string; revenue: number }[];
}

export function RevenueChart({ data }: RevenueChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Revenue Trend</CardTitle>
          <CardDescription>Daily or monthly revenue performance</CardDescription>
        </CardHeader>
        <CardContent className="flex h-72 items-center justify-center text-sm text-muted-foreground">
          No time-series date columns detected in this dataset.
        </CardContent>
      </Card>
    );
  }

  const chartData = data.map((d) => ({
    label: d.date || d.month || "",
    revenue: d.revenue,
  }));

  return (
    <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-base font-semibold">Revenue Trend</CardTitle>
          <CardDescription>Historical sales performance over time</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
              <XAxis
                dataKey="label"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `$${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}`}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const val = Number(payload[0].value);
                    return (
                      <div className="rounded-lg border border-border bg-background p-2.5 shadow-md">
                        <p className="text-xs text-muted-foreground">{payload[0].payload.label}</p>
                        <p className="text-sm font-semibold text-foreground">
                          ${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#revenueGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
