import { Info } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface SkippedSectionProps {
  title: string;
  description: string;
  reason: string;
}

/**
 * Shown instead of a chart/table when the data file doesn't have
 * the columns needed to compute that section.
 * Explains WHY it's missing rather than showing a blank card.
 */
export function SkippedSection({ title, description, reason }: SkippedSectionProps) {
  return (
    <Card className="border-border/60 border-dashed bg-muted/20">
      <CardHeader>
        <CardTitle className="text-base font-semibold text-muted-foreground">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex items-start gap-3 py-6 text-sm text-muted-foreground">
        <Info className="mt-0.5 size-4 shrink-0 text-amber-500" />
        <span>{reason}</span>
      </CardContent>
    </Card>
  );
}
