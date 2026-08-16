"use client";

import {
  Calendar,
  Hash,
  Tag,
  DollarSign,
  Type,
  HelpCircle,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

type ColumnProfile = {
  column_name: string;
  detected_type: string;
  missing_count: number;
  missing_pct: number;
};

type ProfilingResultsProps = {
  rowCount: number;
  duplicateCount: number;
  columns: ColumnProfile[];
  qualityScore: number;
};

const typeIcons: Record<string, React.ElementType> = {
  date: Calendar,
  numeric: Hash,
  categorical: Tag,
  currency: DollarSign,
  text: Type,
  unknown: HelpCircle,
};

const typeLabels: Record<string, string> = {
  date: "Date",
  numeric: "Numeric",
  categorical: "Categorical",
  currency: "Currency",
  text: "Text",
  unknown: "Unknown",
};

function QualityBadge({ score }: { score: number }) {
  const color =
    score >= 90
      ? "text-green-600 bg-green-50 border-green-200"
      : score >= 70
        ? "text-yellow-600 bg-yellow-50 border-yellow-200"
        : "text-red-600 bg-red-50 border-red-200";

  const label = score >= 90 ? "Excellent" : score >= 70 ? "Good" : "Needs attention";

  return (
    <div className={cn("inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium", color)}>
      {score >= 70 ? (
        <CheckCircle2 className="size-4" />
      ) : (
        <AlertTriangle className="size-4" />
      )}
      {score.toFixed(0)}/100 — {label}
    </div>
  );
}

export function ProfilingResults({
  rowCount,
  duplicateCount,
  columns,
  qualityScore,
}: ProfilingResultsProps) {
  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Rows</p>
            <p className="text-2xl font-semibold">{rowCount.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Columns</p>
            <p className="text-2xl font-semibold">{columns.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Duplicates</p>
            <p className="text-2xl font-semibold">{duplicateCount.toLocaleString()}</p>
          </CardContent>
        </Card>
      </div>

      {/* Quality score */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Data Quality Score</CardTitle>
          <CardDescription>
            Based on missing values, duplicates, and type detection.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <QualityBadge score={qualityScore} />
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                qualityScore >= 90
                  ? "bg-green-500"
                  : qualityScore >= 70
                    ? "bg-yellow-500"
                    : "bg-red-500",
              )}
              style={{ width: `${qualityScore}%` }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Columns table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Detected Columns</CardTitle>
          <CardDescription>
            Column types detected automatically from your data.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Column</th>
                  <th className="pb-2 pr-4 font-medium">Type</th>
                  <th className="pb-2 pr-4 font-medium text-right">Missing</th>
                  <th className="pb-2 font-medium text-right">Missing %</th>
                </tr>
              </thead>
              <tbody>
                {columns.map((col) => {
                  const Icon = typeIcons[col.detected_type] ?? HelpCircle;
                  return (
                    <tr
                      key={col.column_name}
                      className="border-b last:border-b-0"
                    >
                      <td className="py-2.5 pr-4 font-medium">
                        {col.column_name}
                      </td>
                      <td className="py-2.5 pr-4">
                        <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-0.5 text-xs font-medium">
                          <Icon className="size-3" />
                          {typeLabels[col.detected_type] ?? col.detected_type}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {col.missing_count}
                      </td>
                      <td
                        className={cn(
                          "py-2.5 text-right tabular-nums",
                          col.missing_pct > 0 && "text-yellow-600",
                          col.missing_pct > 20 && "text-red-600",
                        )}
                      >
                        {col.missing_pct.toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
