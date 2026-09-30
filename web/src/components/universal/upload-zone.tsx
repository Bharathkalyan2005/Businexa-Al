"use client";

import React, { useCallback, useRef, useState } from "react";
import { UploadCloud, FileText, AlertCircle, Loader2, Sparkles } from "lucide-react";
import { generateUniversalDashboard, UniversalDashboardError } from "@/lib/api/universal-dashboard";
import type { UniversalDashboardResponse } from "@/lib/types/universal-dashboard";

interface UploadZoneProps {
  onSuccess: (result: UniversalDashboardResponse) => void;
}

const ACCEPTED = ".csv,.xlsx,.xls";

const SAMPLE_SALES_CSV = `OrderDate,Category,Region,Revenue,Units,CustomerType,Churn
2024-01-05,Electronics,North,1250.50,5,B2B,Active
2024-01-12,Furniture,South,840.00,2,B2C,Active
2024-01-20,Supplies,East,320.10,12,B2C,Churned
2024-02-02,Electronics,West,2100.00,8,B2B,Active
2024-02-14,Furniture,North,950.25,3,B2B,Active
2024-02-28,Supplies,South,410.00,15,B2C,Active
2024-03-05,Electronics,East,1890.00,6,B2C,Churned
2024-03-18,Furniture,West,1200.50,4,B2B,Active
2024-03-25,Supplies,North,530.75,20,B2B,Active
2024-04-02,Electronics,South,2450.00,9,B2B,Active
2024-04-15,Furniture,East,780.00,2,B2C,Active
2024-04-29,Supplies,West,390.50,11,B2C,Churned
2024-05-10,Electronics,North,3100.00,10,B2B,Active
2024-05-22,Furniture,South,1150.00,3,B2C,Active
2024-06-03,Supplies,East,620.00,18,B2B,Active`;

const SAMPLE_CLINICAL_CSV = `PatientID,Age,Gender,BloodPressure,Cholesterol,MaxHeartRate,HeartDisease
P001,54,Male,130,240,150,1
P002,62,Female,145,280,120,1
P003,41,Male,120,190,172,0
P004,58,Female,138,260,135,1
P005,39,Female,115,175,180,0
P006,67,Male,150,310,110,1
P007,48,Male,128,215,160,0
P008,52,Female,135,230,145,0
P009,61,Male,142,275,128,1
P010,44,Female,122,195,168,0
P011,59,Male,148,290,125,1
P012,36,Male,118,180,175,0`;

export function UploadZone({ onSuccess }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [stage, setStage] = useState<"idle" | "profiling" | "generating" | "done">("idle");
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setSelectedFile(file);
      setError(null);
      setIsLoading(true);
      setStage("profiling");

      try {
        // Simulate stage messages
        const timer = setTimeout(() => setStage("generating"), 2500);
        const result = await generateUniversalDashboard(file);
        clearTimeout(timer);
        setStage("done");
        onSuccess(result);
      } catch (err) {
        const msg =
          err instanceof UniversalDashboardError
            ? err.detail
            : err instanceof Error
            ? err.message
            : "An unexpected error occurred.";
        setError(msg);
        setStage("idle");
      } finally {
        setIsLoading(false);
      }
    },
    [onSuccess],
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const stageMessages: Record<string, string> = {
    profiling: "Stage 1 — Profiling your data…",
    generating: "Stage 2 — Generating dashboard spec with AI…",
    done: "All done! Building your dashboard…",
  };

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload CSV or Excel file"
        onClick={() => !isLoading && inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && !isLoading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        className={[
          "relative flex w-full max-w-xl cursor-pointer flex-col items-center justify-center gap-4",
          "rounded-3xl border-2 border-dashed px-8 py-16 text-center",
          "transition-all duration-200 select-none",
          isDragging
            ? "border-primary bg-primary/5 scale-[1.02]"
            : "border-border bg-card hover:border-primary/40 hover:bg-muted/30",
          isLoading && "pointer-events-none opacity-80",
        ].join(" ")}
      >
        {isLoading ? (
          <>
            <div className="relative">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
            <p className="text-sm font-semibold text-foreground">
              {stageMessages[stage] ?? "Processing…"}
            </p>
            {selectedFile && (
              <p className="text-xs text-muted-foreground">{selectedFile.name}</p>
            )}
            {/* Progress bar */}
            <div className="w-full max-w-xs rounded-full bg-muted h-1.5 overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all duration-700"
                style={{ width: stage === "profiling" ? "40%" : stage === "generating" ? "80%" : "100%" }}
              />
            </div>
          </>
        ) : (
          <>
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <UploadCloud className="h-8 w-8 text-primary" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-base font-semibold text-foreground">
                Drop any CSV or Excel file here
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                or <span className="text-primary font-medium underline underline-offset-2">browse to upload</span>
              </p>
            </div>
            <p className="text-xs text-muted-foreground/70">
              Supports .csv, .xlsx, .xls — up to 50 MB
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="sr-only"
          onChange={onInputChange}
          disabled={isLoading}
        />
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex w-full max-w-xl items-start gap-3 rounded-2xl border border-destructive/30 bg-destructive/10 px-4 py-3">
          <AlertCircle className="h-5 w-5 shrink-0 text-destructive mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-destructive">Could not generate dashboard</p>
            <p className="text-xs text-destructive/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Quick-start sample datasets */}
      <div className="flex flex-col items-center gap-2 pt-2">
        <p className="text-xs font-medium text-muted-foreground">Or try an instant sample:</p>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            disabled={isLoading}
            onClick={() => {
              const file = new File([SAMPLE_SALES_CSV], "enterprise_sales_sample.csv", { type: "text/csv" });
              handleFile(file);
            }}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground shadow-sm transition-all hover:border-primary/50 hover:bg-muted/50 disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            Enterprise Sales (.csv)
          </button>
          <button
            type="button"
            disabled={isLoading}
            onClick={() => {
              const file = new File([SAMPLE_CLINICAL_CSV], "clinical_records_sample.csv", { type: "text/csv" });
              handleFile(file);
            }}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground shadow-sm transition-all hover:border-primary/50 hover:bg-muted/50 disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            Clinical Records (.csv)
          </button>
        </div>
      </div>

      {/* Example formats */}
      <div className="flex gap-3 text-xs text-muted-foreground/70">
        {["Sales data", "Clinical records", "HR surveys", "Sports stats"].map((ex) => (
          <span key={ex} className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5" />
            {ex}
          </span>
        ))}
      </div>
    </div>
  );
}
