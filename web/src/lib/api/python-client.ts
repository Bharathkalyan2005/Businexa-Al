/**
 * Typed HTTP client for calling the Python FastAPI service.
 * Sends the shared INTERNAL_API_KEY on every request.
 */

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";

interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
}

class PythonApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "PythonApiError";
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = process.env.PYTHON_API_URL || "http://localhost:8000";
  const apiKey = process.env.INTERNAL_API_KEY || "bizlens_internal_secret_key_2025";

  const url = `${baseUrl}${path}`;
  const { method = "GET", body, headers = {} } = options;

  const res = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Api-Key": apiKey,
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const errorBody = (await res.json()) as { detail?: string };
      if (errorBody.detail) {
        detail = errorBody.detail;
      }
    } catch {
      // Ignore parse failure
    }
    throw new PythonApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

// ─── Response types ──────────────────────────────────────────────────────

export interface ColumnProfile {
  column_name: string;
  detected_type: string;
  missing_count: number;
  missing_pct: number;
}

export interface ProfilingResult {
  dataset_id: string;
  row_count: number;
  duplicate_count: number;
  columns: ColumnProfile[];
  quality_score: number;
}

export interface DatasetStatus {
  dataset_id: string;
  status: string;
}

export interface AnalysisResult {
  dataset_id: string;
  snapshot_id: string;
  status: string;
  metrics: {
    business_type: string;
    row_count: number;
    revenue: number | null;
    orders: number;
    average_order_value: number;
    growth_pct: number | null;
    profit: number | null;
    profit_margin: number | null;
    top_product: string | null;
    top_products: { product: string; revenue: number; pct_of_total: number }[];
    bottom_products: { product: string; revenue: number; pct_of_total: number }[];
    revenue_by_day?: { date: string; revenue: number }[];
    revenue_by_month?: { month: string; revenue: number }[];
    profit_by_day?: { date: string; profit: number }[];
    customer_count?: number | null;
    repeat_customer_rate?: number | null;
  };
  insights: { text: string; category: "growth" | "profitability" | "anomaly" | "product" }[];
}

export interface ChatResponse {
  answer: string;
  business_id: string;
}

export interface ReportResponse {
  report_id: string;
  pdf_url: string;
  generated_at: string;
}

// ─── API methods ─────────────────────────────────────────────────────────

export async function profileDataset(
  datasetId: string,
  blobUrl: string,
  businessType: string,
): Promise<ProfilingResult> {
  return request<ProfilingResult>(`/datasets/${datasetId}/profile`, {
    method: "POST",
    body: { blob_url: blobUrl, business_type: businessType },
  });
}

export async function cleanDataset(
  datasetId: string,
  blobUrl: string,
  businessType: string,
): Promise<{ status: string; summary: Record<string, unknown> }> {
  return request(`/datasets/${datasetId}/clean`, {
    method: "POST",
    body: { blob_url: blobUrl, business_type: businessType },
  });
}

export async function analyzeDataset(
  datasetId: string,
  blobUrl: string,
  businessType: string,
): Promise<AnalysisResult> {
  return request<AnalysisResult>(`/datasets/${datasetId}/analyze`, {
    method: "POST",
    body: { blob_url: blobUrl, business_type: businessType },
  });
}

export async function getDatasetStatus(datasetId: string): Promise<DatasetStatus> {
  return request<DatasetStatus>(`/datasets/${datasetId}/status`);
}

export async function sendChatMessage(
  businessId: string,
  question: string,
): Promise<ChatResponse> {
  return request<ChatResponse>("/ai/chat", {
    method: "POST",
    body: { business_id: businessId, question },
  });
}

export async function generatePdfReport(
  businessId: string,
  datasetId: string,
): Promise<ReportResponse> {
  return request<ReportResponse>("/reports/generate", {
    method: "POST",
    body: { business_id: businessId, dataset_id: datasetId },
  });
}

export { PythonApiError };
