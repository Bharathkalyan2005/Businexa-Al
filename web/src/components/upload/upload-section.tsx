"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

import { Dropzone } from "@/components/upload/dropzone";
import { ProfilingResults } from "@/components/upload/profiling-results";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileSpreadsheet, ArrowRight } from "lucide-react";

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
  error?: string;
};

type UploadSectionProps = {
  businessId: string;
  existingDatasets: DatasetWithColumns[];
};

export function UploadSection({
  businessId,
  existingDatasets,
}: UploadSectionProps) {
  const router = useRouter();
  const [lastUpload, setLastUpload] = useState<UploadResponse | null>(null);

  const handleUploadComplete = useCallback((response: UploadResponse) => {
    setLastUpload(response);
  }, []);

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
            <h2 className="text-lg font-semibold">
              Profiling Results — {lastUpload.dataset?.filename}
            </h2>
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
              <Card key={ds.id}>
                <CardContent className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="size-5 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{ds.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(ds.uploadedAt).toLocaleDateString()} ·{" "}
                        {ds.columns.length} columns · Status: {ds.status}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
