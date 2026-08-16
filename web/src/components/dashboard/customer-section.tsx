import { HeartHandshake, UserCheck, Users } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface CustomerSectionProps {
  customerCount: number | null | undefined;
  repeatCustomerRate: number | null | undefined;
}

export function CustomerSection({
  customerCount,
  repeatCustomerRate,
}: CustomerSectionProps) {
  if (customerCount === null || customerCount === undefined) {
    return null; // As per specification: only render if customer data exists in dataset
  }

  return (
    <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold">Customer Performance</CardTitle>
            <CardDescription>Audience engagement & loyalty metrics</CardDescription>
          </div>
          <Users className="size-5 text-indigo-500" />
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-muted/20 p-4">
          <div className="rounded-lg bg-indigo-500/10 p-2.5 text-indigo-600 dark:text-indigo-400">
            <UserCheck className="size-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Unique Customers</p>
            <p className="text-xl font-bold">{customerCount.toLocaleString()}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-muted/20 p-4">
          <div className="rounded-lg bg-emerald-500/10 p-2.5 text-emerald-600 dark:text-emerald-400">
            <HeartHandshake className="size-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Repeat Customer Rate</p>
            <p className="text-xl font-bold">
              {repeatCustomerRate !== null && repeatCustomerRate !== undefined ? `${repeatCustomerRate}%` : "—"}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
