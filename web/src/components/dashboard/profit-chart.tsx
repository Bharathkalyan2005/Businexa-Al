"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface ProfitChartProps {
  data: { date: string; profit: number }[];
}

export function ProfitChart({ data }: ProfitChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Profit Breakdown</CardTitle>
          <CardDescription>Daily net profitability</CardDescription>
        </CardHeader>
        <CardContent className="flex h-72 items-center justify-center text-sm text-muted-foreground">
          No cost columns provided in this dataset to compute daily profit.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-base font-semibold">Profit by Day</CardTitle>
          <CardDescription>Daily net earnings tracking</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
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
                        <p className="text-xs text-muted-foreground">{payload[0].payload.date}</p>
                        <p className="text-sm font-semibold text-foreground">
                          ${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="profit" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
