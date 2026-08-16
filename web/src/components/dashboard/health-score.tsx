import { ShieldCheck } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface HealthScoreProps {
  growthPct: number | null;
  profitMargin: number | null;
  repeatRate: number | null;
  orders: number | null;
}

export function computeBusinessHealthScore({
  growthPct,
  profitMargin,
  repeatRate,
  orders,
}: HealthScoreProps): { score: number; label: string; components: { name: string; score: number; weight: string }[] } {
  // Composite score components (0-100 scale):
  // 1. Growth Stability (30% weight)
  let growthScore = 70;
  if (growthPct !== null) {
    if (growthPct >= 20) growthScore = 100;
    else if (growthPct >= 10) growthScore = 90;
    else if (growthPct >= 0) growthScore = 75;
    else if (growthPct >= -10) growthScore = 50;
    else growthScore = 30;
  }

  // 2. Profitability (30% weight)
  let profitScore = 70;
  if (profitMargin !== null) {
    if (profitMargin >= 25) profitScore = 100;
    else if (profitMargin >= 15) profitScore = 85;
    else if (profitMargin >= 5) profitScore = 70;
    else if (profitMargin >= 0) profitScore = 50;
    else profitScore = 20;
  }

  // 3. Customer Retention (20% weight)
  let retentionScore = 65;
  if (repeatRate !== null && repeatRate !== undefined) {
    if (repeatRate >= 40) retentionScore = 95;
    else if (repeatRate >= 20) retentionScore = 80;
    else retentionScore = 60;
  }

  // 4. Order Volume & Activity (20% weight)
  let volumeScore = 80;
  if (orders !== null && orders > 0) {
    if (orders >= 100) volumeScore = 95;
    else if (orders >= 20) volumeScore = 85;
    else volumeScore = 70;
  }

  const finalScore = Math.round(
    growthScore * 0.3 + profitScore * 0.3 + retentionScore * 0.2 + volumeScore * 0.2
  );

  let label = "Excellent";
  if (finalScore < 60) label = "Needs Attention";
  else if (finalScore < 75) label = "Fair";
  else if (finalScore < 88) label = "Good";

  return {
    score: finalScore,
    label,
    components: [
      { name: "Revenue Growth", score: growthScore, weight: "30%" },
      { name: "Profit Margin", score: profitScore, weight: "30%" },
      { name: "Customer Retention", score: retentionScore, weight: "20%" },
      { name: "Activity Volume", score: volumeScore, weight: "20%" },
    ],
  };
}

export function HealthScore({
  growthPct,
  profitMargin,
  repeatRate,
  orders,
}: HealthScoreProps) {
  const health = computeBusinessHealthScore({ growthPct, profitMargin, repeatRate, orders });

  const colorClass =
    health.score >= 80
      ? "text-emerald-600 dark:text-emerald-400"
      : health.score >= 65
      ? "text-blue-600 dark:text-blue-400"
      : health.score >= 50
      ? "text-amber-600 dark:text-amber-400"
      : "text-rose-600 dark:text-rose-400";

  return (
    <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold">Business Health Score</CardTitle>
            <CardDescription>Composite operational & financial rating</CardDescription>
          </div>
          <ShieldCheck className="size-5 text-primary" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center pb-4 text-center sm:flex-row sm:justify-between sm:text-left">
          <div className="flex items-baseline gap-2">
            <span className={cn("text-5xl font-extrabold tracking-tight", colorClass)}>
              {health.score}
            </span>
            <span className="text-sm font-medium text-muted-foreground">/100</span>
          </div>
          <div className="mt-2 sm:mt-0">
            <span className={cn("inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider", colorClass)}>
              {health.label}
            </span>
          </div>
        </div>

        <div className="mt-4 space-y-2 border-t border-border/60 pt-4">
          {health.components.map((c) => (
            <div key={c.name} className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{c.name} ({c.weight})</span>
              <span className="font-medium text-foreground">{c.score}/100</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
