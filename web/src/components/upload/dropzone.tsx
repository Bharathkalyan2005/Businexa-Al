"use client";

import { useCallback, useState, useRef } from "react";
import { Upload, FileSpreadsheet, X, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type UploadState = "idle" | "uploading" | "success" | "error";

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

type DropzoneProps = {
  businessId: string;
  onUploadComplete?: (response: UploadResponse) => void;
};

const ACCEPTED_EXTENSIONS = [".csv", ".xlsx"];
const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024;

export function Dropzone({ businessId, onUploadComplete }: DropzoneProps) {
  const [state, setState] = useState<UploadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): string | null => {
    const name = file.name.toLowerCase();
    const ext = name.substring(name.lastIndexOf("."));

    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      return `Unsupported file type. Please upload a ${ACCEPTED_EXTENSIONS.join(" or ")} file.`;
    }

    if (file.size > MAX_FILE_SIZE) {
      return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum size is ${MAX_FILE_SIZE_MB} MB.`;
    }

    return null;
  }, []);

  const handleFile = useCallback(
    (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      setError(null);
      setSelectedFile(file);
    },
    [validateFile],
  );

  const uploadFile = useCallback(async () => {
    if (!selectedFile) return;

    setState("uploading");
    setError(null);
    setProgress(10);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("businessId", businessId);

      setProgress(30);

      const res = await fetch("/api/datasets/upload", {
        method: "POST",
        body: formData,
      });

      setProgress(70);

      const data = (await res.json()) as UploadResponse;

      if (!res.ok || data.error) {
        setState("error");
        setError(data.error ?? `Upload failed (HTTP ${res.status})`);
        return;
      }

      setProgress(100);
      setState("success");
      onUploadComplete?.(data);
    } catch (err) {
      setState("error");
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred.",
      );
    }
  }, [selectedFile, businessId, onUploadComplete]);

  const reset = useCallback(() => {
    setState("idle");
    setError(null);
    setSelectedFile(null);
    setProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile],
  );

  return (
    <div className="space-y-4">
      {/* Dropzone area */}
      <Card
        className={cn(
          "border-2 border-dashed transition-colors cursor-pointer",
          dragActive && "border-primary bg-primary/5",
          state === "error" && "border-destructive/50",
          state === "success" && "border-green-500/50",
          !dragActive && state === "idle" && "hover:border-primary/50",
        )}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => state === "idle" && fileInputRef.current?.click()}
      >
        <CardContent className="flex flex-col items-center justify-center gap-3 py-12">
          {state === "uploading" ? (
            <>
              <Loader2 className="size-10 animate-spin text-primary" />
              <p className="text-sm font-medium">
                {progress < 50
                  ? "Uploading file..."
                  : "Profiling your data..."}
              </p>
              <div className="h-2 w-48 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </>
          ) : selectedFile ? (
            <>
              <FileSpreadsheet className="size-10 text-primary" />
              <div className="text-center">
                <p className="text-sm font-medium">{selectedFile.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <div className="flex gap-2">
                <Button onClick={uploadFile} size="sm">
                  <Upload className="mr-2 size-4" />
                  Upload & Profile
                </Button>
                <Button onClick={reset} variant="outline" size="sm">
                  <X className="mr-2 size-4" />
                  Remove
                </Button>
              </div>
            </>
          ) : (
            <>
              <Upload className="size-10 text-muted-foreground" />
              <div className="text-center">
                <p className="text-sm font-medium">
                  Drop your file here or click to browse
                </p>
                <p className="text-xs text-muted-foreground">
                  Supports .csv and .xlsx files up to {MAX_FILE_SIZE_MB} MB
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx"
        onChange={handleInputChange}
        className="hidden"
      />

      {/* Error message */}
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
          <p className="text-sm text-destructive">{error}</p>
          {state === "error" && (
            <Button
              onClick={reset}
              variant="outline"
              size="sm"
              className="mt-2"
            >
              Try again
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
