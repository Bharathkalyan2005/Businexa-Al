"use client";

import { useState, useTransition } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { triggerReportGeneration } from "@/actions/reports";

interface GenerateButtonProps {
  businessId: string;
}

export function GenerateButton({ businessId }: GenerateButtonProps) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = () => {
    setError(null);
    startTransition(async () => {
      const res = await triggerReportGeneration(businessId);
      if (res.error) {
        setError(res.error);
      }
    });
  };

  return (
    <div className="space-y-2">
      <Button onClick={handleGenerate} disabled={isPending} className="gap-2">
        {isPending ? (
          <>
            <Loader2 className="size-4 animate-spin" />
            Generating Executive PDF...
          </>
        ) : (
          <>
            <Sparkles className="size-4" />
            Generate New Report
          </>
        )}
      </Button>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
