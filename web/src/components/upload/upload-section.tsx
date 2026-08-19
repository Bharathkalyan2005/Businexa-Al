"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

import { Dropzone } from "@/components/upload/dropzone";
import { ProfilingResults } from "@/components/upload/profiling-results";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  FileSpreadsheet,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

import type { DatasetWithColumns } from "@/actions/datasets";

type UploadResponse = {
  dataset?: {
    id: string;
    filename: string;
    storageUrl: string;
    status: string;
  };
  profiling?: {
    dataset_id: string;
    row_count: number;
    duplicate_count: number;
    columns: {
      column_name: string;
      detected_type: string;
      missing_count: number;
      missing_pct: number;
    }[];
    quality_score: number;
  };
  analysis?: unknown;
  error?: string;
};

type UploadSectionProps = {
  businessId: string;
  existingDatasets: DatasetWithColumns[];
};

function renderStatusBadge(status: string) {
  switch (status) {
    case "analyzed":
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-500">
          <CheckCircle2 className="size-3.5" />
          Analyzed & Ready
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-destructive/10 px-2.5 py-0.5 text-xs font-semibold text-destructive">
          <AlertCircle className="size-3.5" />
          Processing Failed
        </span>
      );
    case "profiling":
    case "cleaning":
    case "analyzing":
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-semibold text-blue-500">
          <Loader2 className="size-3.5 animate-spin" />
          Processing...
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-500">
          <Clock className="size-3.5" />
          Pending Analysis
        </span>
      );
  }
}

export function UploadSection({
  businessId,
  existingDatasets,
}: UploadSectionProps) {
  const router = useRouter();
  const [lastUpload, setLastUpload] = useState<UploadResponse | null>(null);

  const handleUploadComplete = useCallback(
    (response: UploadResponse) => {
      setLastUpload(response);
      router.refresh();
    },
    [router],
  );

  return (
    <div className="space-y-8">
      {/* Upload dropzone */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Upload new dataset</h2>
        <Dropzone
          businessId={businessId}
          onUploadComplete={handleUploadComplete}
        />
      </div>

      {/* Profiling results (after upload) */}
      {lastUpload?.profiling && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">
                Profiling & Analysis Results — {lastUpload.dataset?.filename}
              </h2>
              <p className="text-xs text-muted-foreground">
                Dataset successfully analyzed and ready for dashboard reporting.
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => router.push(`/dashboard/${businessId}`)}
            >
              Go to Dashboard
              <ArrowRight className="ml-2 size-4" />
            </Button>
          </div>
          <ProfilingResults
            rowCount={lastUpload.profiling.row_count}
            duplicateCount={lastUpload.profiling.duplicate_count}
            columns={lastUpload.profiling.columns}
            qualityScore={lastUpload.profiling.quality_score}
          />
        </div>
      )}

      {/* Previously uploaded datasets */}
      {existingDatasets.length > 0 && (
        <div>
          <h2 className="mb-4 text-lg font-semibold">Previous uploads</h2>
          <div className="space-y-2">
            {existingDatasets.map((ds) => (
              <Card
                key={ds.id}
                className={cn(
                  "transition-colors",
                  ds.status === "failed" && "border-destructive/30 bg-destructive/5",
                )}
              >
                <CardContent className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet
                      className={cn(
                        "size-5",
                        ds.status === "failed"
                          ? "text-destructive"
                          : "text-muted-foreground",
                      )}
                    />
                    <div>
                      <p className="text-sm font-medium">{ds.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(ds.uploadedAt).toLocaleDateString()} ·{" "}
                        {ds.columns.length} columns detected
                      </p>
                    </div>
                  </div>
                  <div>{renderStatusBadge(ds.status)}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
