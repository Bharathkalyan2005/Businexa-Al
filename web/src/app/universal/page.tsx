"use client";

import React, { useState } from "react";
import { Sparkles } from "lucide-react";
import type { UniversalDashboardResponse } from "@/lib/types/universal-dashboard";
import { UploadZone } from "@/components/universal/upload-zone";
import { DashboardView } from "@/components/universal/dashboard-view";

export default function UniversalDashboardPage() {
  const [result, setResult] = useState<UniversalDashboardResponse | null>(null);

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">

        {!result ? (
          /* ── Upload / landing state ─────────────────────────────────── */
          <div className="flex flex-col items-center justify-center min-h-screen gap-12 py-20">
            {/* Hero */}
            <div className="text-center max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-semibold text-primary uppercase tracking-widest mb-6">
                <Sparkles className="h-3.5 w-3.5" />
                Universal Dashboard
              </div>
              <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
                Upload any data.<br />
                <span className="text-primary">Get an instant dashboard.</span>
              </h1>
              <p className="mt-5 text-base text-muted-foreground leading-relaxed max-w-xl mx-auto">
                Drop any CSV or Excel file — sales, clinical records, HR data, sports stats,
                anything. The system profiles your data and AI generates a tailored
                interactive dashboard automatically.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-3 text-sm text-muted-foreground">
                {[
                  "No templates",
                  "No hardcoded schemas",
                  "AI-selected charts",
                  "Precomputed stats only",
                ].map((feat) => (
                  <span key={feat} className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary/60" />
                    {feat}
                  </span>
                ))}
              </div>
            </div>

            <UploadZone onSuccess={setResult} />
          </div>
        ) : (
          /* ── Dashboard state ─────────────────────────────────────────── */
          <div className="py-8 lg:py-12">
            <DashboardView
              data={result}
              onReset={() => setResult(null)}
            />
          </div>
        )}
      </div>
    </main>
  );
}
