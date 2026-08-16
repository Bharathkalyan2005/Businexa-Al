import Link from "next/link";
import { FileSpreadsheet, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface EmptyStateProps {
  businessId: string;
  businessName: string;
}

export function EmptyState({ businessId, businessName }: EmptyStateProps) {
  return (
    <Card className="border-border/80 bg-card/40 backdrop-blur-sm">
      <CardContent className="flex flex-col items-center justify-center gap-6 py-20 text-center">
        <div className="flex size-16 items-center justify-center rounded-2xl bg-primary/10 text-primary ring-8 ring-primary/5">
          <FileSpreadsheet className="size-8" />
        </div>
        <div className="max-w-md space-y-2">
          <h2 className="text-xl font-bold tracking-tight">No data uploaded yet</h2>
          <p className="text-sm text-muted-foreground">
            Upload your CSV or Excel sales spreadsheet for <span className="font-semibold text-foreground">{businessName}</span> to automatically calculate KPIs, detect anomalies, and generate AI insights.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Link href={`/dashboard/${businessId}/upload`}>
            <Button size="lg" className="gap-2">
              <Upload className="size-4" />
              Upload Sales Data
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
