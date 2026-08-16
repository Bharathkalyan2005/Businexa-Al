import { AlertCircle, ArrowUpRight, Lightbulb, Sparkles, TrendingUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface InsightItem {
  id?: string;
  insightText: string;
  category: "growth" | "profitability" | "anomaly" | "product" | string;
}

interface InsightsCardsProps {
  insights: InsightItem[];
}

const categoryIcons = {
  growth: TrendingUp,
  profitability: ArrowUpRight,
  anomaly: AlertCircle,
  product: Sparkles,
};

const categoryBadgeStyles = {
  growth: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  profitability: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  anomaly: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
  product: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
};

export function InsightsCards({ insights }: InsightsCardsProps) {
  if (!insights || insights.length === 0) {
    return (
      <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">AI Business Insights</CardTitle>
          <CardDescription>Automated trend analysis and notifications</CardDescription>
        </CardHeader>
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          No insights generated yet. Upload data to get automated findings.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold">AI Business Insights</CardTitle>
            <CardDescription>Verified analysis and key business patterns</CardDescription>
          </div>
          <Lightbulb className="size-5 text-amber-500" />
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {insights.map((item, idx) => {
          const category = (item.category || "growth") as keyof typeof categoryIcons;
          const Icon = categoryIcons[category] || TrendingUp;
          const badgeClass = categoryBadgeStyles[category] || categoryBadgeStyles.growth;

          return (
            <div
              key={item.id || idx}
              className="flex items-start gap-3 rounded-lg border border-border/60 bg-muted/20 p-4 transition-colors hover:bg-muted/40"
            >
              <div className={cn("mt-0.5 rounded-md border p-1.5", badgeClass)}>
                <Icon className="size-4" />
              </div>
              <div className="space-y-1">
                <span className={cn("inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider", badgeClass)}>
                  {category}
                </span>
                <p className="text-sm font-medium leading-relaxed text-foreground">
                  {item.insightText}
                </p>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
