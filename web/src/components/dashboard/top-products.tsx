import { Award } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface TopProductsProps {
  products: { product: string; revenue: number; pct_of_total: number }[];
}

export function TopProducts({ products }: TopProductsProps) {
  if (!products || products.length === 0) {
    return (
      <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Top Products</CardTitle>
          <CardDescription>Highest revenue generating items</CardDescription>
        </CardHeader>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          No product column detected in this dataset.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold">Top Products</CardTitle>
            <CardDescription>By revenue share</CardDescription>
          </div>
          <Award className="size-5 text-amber-500" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {products.map((item, idx) => (
          <div key={item.product} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="flex size-5 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                  {idx + 1}
                </span>
                <span className="font-medium">{item.product}</span>
              </div>
              <div className="text-right">
                <span className="font-semibold">${item.revenue.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
                <span className="ml-1 text-xs text-muted-foreground">({item.pct_of_total}%)</span>
              </div>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${Math.min(item.pct_of_total, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
