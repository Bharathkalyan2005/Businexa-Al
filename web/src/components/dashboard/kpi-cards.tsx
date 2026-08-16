import { ArrowDownRight, ArrowUpRight, DollarSign, Package, ShoppingCart, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KpiCardsProps {
  revenue: number | null;
  profit: number | null;
  orders: number | null;
  aov: number | null;
  growthPct: number | null;
  profitMargin: number | null;
}

export function KpiCards({
  revenue,
  profit,
  orders,
  aov,
  growthPct,
  profitMargin,
}: KpiCardsProps) {
  const isPositiveGrowth = growthPct !== null && growthPct >= 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* Revenue */}
      <Card className="relative overflow-hidden border-border/80 bg-card/60 backdrop-blur-sm transition-all hover:border-primary/40 hover:shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Revenue
            </span>
            <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400">
              <DollarSign className="size-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <p className="text-2xl font-bold tracking-tight">
              {revenue !== null ? `$${revenue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
            </p>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-xs">
            {growthPct !== null ? (
              <span
                className={cn(
                  "inline-flex items-center font-medium",
                  isPositiveGrowth ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                )}
              >
                {isPositiveGrowth ? <ArrowUpRight className="mr-0.5 size-3.5" /> : <ArrowDownRight className="mr-0.5 size-3.5" />}
                {Math.abs(growthPct)}%
              </span>
            ) : (
              <span className="text-muted-foreground">Baseline period</span>
            )}
            <span className="text-muted-foreground">vs previous</span>
          </div>
        </CardContent>
      </Card>

      {/* Profit */}
      <Card className="relative overflow-hidden border-border/80 bg-card/60 backdrop-blur-sm transition-all hover:border-primary/40 hover:shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Net Profit
            </span>
            <div className="rounded-lg bg-blue-500/10 p-2 text-blue-600 dark:text-blue-400">
              <TrendingUp className="size-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <p className="text-2xl font-bold tracking-tight">
              {profit !== null ? `$${profit.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
            </p>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
            {profitMargin !== null ? (
              <span className="font-medium text-blue-600 dark:text-blue-400">
                {profitMargin}% margin
              </span>
            ) : (
              <span>Cost data not provided</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Orders */}
      <Card className="relative overflow-hidden border-border/80 bg-card/60 backdrop-blur-sm transition-all hover:border-primary/40 hover:shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Orders
            </span>
            <div className="rounded-lg bg-indigo-500/10 p-2 text-indigo-600 dark:text-indigo-400">
              <ShoppingCart className="size-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <p className="text-2xl font-bold tracking-tight">
              {orders !== null ? orders.toLocaleString() : "0"}
            </p>
          </div>
          <div className="mt-2 text-xs text-muted-foreground">
            Total sales transactions
          </div>
        </CardContent>
      </Card>

      {/* Average Order Value */}
      <Card className="relative overflow-hidden border-border/80 bg-card/60 backdrop-blur-sm transition-all hover:border-primary/40 hover:shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Avg Order Value
            </span>
            <div className="rounded-lg bg-amber-500/10 p-2 text-amber-600 dark:text-amber-400">
              <Package className="size-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <p className="text-2xl font-bold tracking-tight">
              {aov !== null ? `$${aov.toFixed(2)}` : "—"}
            </p>
          </div>
          <div className="mt-2 text-xs text-muted-foreground">
            Per transaction average
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
