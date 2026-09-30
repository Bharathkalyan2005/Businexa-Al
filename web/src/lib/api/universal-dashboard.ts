/**
 * API client function for the Universal Dashboard pipeline.
 * Sends a file upload to POST /universal/generate and returns the
 * full dashboard response (Stage 1 profile + Stage 2 spec + resolved KPI values).
 */

import type { UniversalDashboardResponse } from "@/lib/types/universal-dashboard";

export class UniversalDashboardError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "UniversalDashboardError";
  }
}

export async function generateUniversalDashboard(
  file: File,
): Promise<UniversalDashboardResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_PYTHON_API_URL || "http://localhost:8000";

  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${baseUrl}/universal/generate`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new UniversalDashboardError(res.status, detail);
  }

  return res.json() as Promise<UniversalDashboardResponse>;
}
