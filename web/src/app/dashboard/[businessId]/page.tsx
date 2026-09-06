import { notFound } from "next/navigation";

import { getDashboardData } from "@/actions/dashboard";
import { getCurrentUser } from "@/lib/auth/get-current-user";
import { DashboardHeader } from "@/components/layout/dashboard-header";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { RevenueChart } from "@/components/dashboard/revenue-chart";
import { ProfitChart } from "@/components/dashboard/profit-chart";
import { TopProducts } from "@/components/dashboard/top-products";
import { CustomerSection } from "@/components/dashboard/customer-section";
import { InsightsCards } from "@/components/dashboard/insights-cards";
import { HealthScore } from "@/components/dashboard/health-score";
import { EmptyState } from "@/components/dashboard/empty-state";
import { ChatPanel } from "@/components/chat/chat-panel";
import { SkippedSection } from "@/components/dashboard/skipped-section";

type DashboardPageProps = PageProps<"/dashboard/[businessId]">;

interface SkippedMetric {
  metric: string;
  reason: string;
}

interface ResolvedColumns {
  date?: string | null;
  revenue?: string | null;
  product?: string | null;
  quantity?: string | null;
  cost?: string | null;
  customer?: string | null;
  status?: string | null;
}

interface DashboardMetrics {
  available_sections?: string[];
  skipped_metrics?: SkippedMetric[];
  resolved_columns?: ResolvedColumns;
  average_order_value?: number | null;
  profit_margin?: number | null;
  total_quantity?: number | null;
  revenue_by_day?: { date: string; revenue: number }[];
  revenue_by_month?: { month: string; revenue: number }[];
  profit_by_day?: { date: string; profit: number }[];
  top_products?: { product: string; revenue: number; pct_of_total: number }[];
  customer_count?: number | null;
  repeat_customer_rate?: number | null;
}

export default async function DashboardPage({ params }: DashboardPageProps) {
  const { businessId } = await params;
  const [user, data] = await Promise.all([
    getCurrentUser(),
    getDashboardData(businessId),
  ]);

  if (!data || !data.business) {
    notFound();
  }

  const { business, dataset, snapshot, insightsList, chatHistory } = data;
  const greetingName = user?.name?.split(" ")[0] ?? "there";
  const metrics = snapshot?.rawJson as DashboardMetrics | undefined;

  // Derive what sections are actually available from the data
  const sections = new Set(metrics?.available_sections ?? []);
  const skipped = metrics?.skipped_metrics ?? [];
  const resolved = metrics?.resolved_columns ?? {};

  // Helper: get the skip reason for a given metric key
  const skipReasonFor = (metric: string) =>
    skipped.find((s) => s.metric === metric)?.reason ?? null;

  // Revenue trend data: prefer daily if ≥2 points, else monthly
  const revenueData =
    (metrics?.revenue_by_day?.length ?? 0) >= 2
      ? metrics!.revenue_by_day!
      : (metrics?.revenue_by_month ?? []);

  // Use detected column names as labels so the UI reflects the actual file
  const revenueLabel = resolved.revenue ?? "Revenue";
  const productLabel = resolved.product ?? "Product";
  const customerLabel = resolved.customer ?? "Customer";

  return (
    <>
      <DashboardHeader
        title={`Good morning, ${greetingName}`}
        description={`Here's what's happening in ${business.name}.`}
      />

      <main className="flex-1 space-y-8 p-8">
        {!dataset || !snapshot || !metrics ? (
          <EmptyState businessId={businessId} businessName={business.name} />
        ) : (
          <>
            {/* ── KPI Cards: only show values where data exists ── */}
            <KpiCards
              revenue={sections.has("revenue") && snapshot.revenue != null ? Number(snapshot.revenue) : null}
              profit={sections.has("profit") && snapshot.profit != null ? Number(snapshot.profit) : null}
              orders={snapshot.orders != null ? Number(snapshot.orders) : null}
              aov={sections.has("revenue") ? (metrics.average_order_value ?? null) : null}
              growthPct={snapshot.growthPct != null ? Number(snapshot.growthPct) : null}
              profitMargin={sections.has("profit") ? (metrics.profit_margin ?? null) : null}
              totalQuantity={sections.has("quantity") ? (metrics.total_quantity ?? null) : null}
              revenueLabel={revenueLabel}
              skippedRevenue={!sections.has("revenue") ? skipReasonFor("revenue") : null}
              skippedProfit={!sections.has("profit") ? skipReasonFor("profit_margin") : null}
            />

            {/* ── Revenue Trend & Profit Breakdown ── */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {sections.has("revenue_trend") ? (
                <RevenueChart data={revenueData} label={revenueLabel} />
              ) : (
                <SkippedSection
                  title="Revenue Trend"
                  description="Sales performance over time"
                  reason={skipReasonFor("revenue_trend") ?? "No time-series data available."}
                />
              )}

              {sections.has("profit_trend") ? (
                <ProfitChart data={metrics.profit_by_day ?? []} />
              ) : (
                <SkippedSection
                  title="Profit Breakdown"
                  description="Net profitability over time"
                  reason={skipReasonFor("profit_trend") ?? "No cost data available."}
                />
              )}
            </div>

            {/* ── Top Products & Customer Performance ── */}
            {(sections.has("top_products") || sections.has("customers")) && (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {sections.has("top_products") && (
                  <TopProducts
                    products={metrics.top_products ?? []}
                    label={productLabel}
                  />
                )}
                {sections.has("customers") && (
                  <CustomerSection
                    customerCount={metrics.customer_count}
                    repeatCustomerRate={metrics.repeat_customer_rate}
                    label={customerLabel}
                  />
                )}
              </div>
            )}

            {/* ── AI Insights & Health Score ── */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <InsightsCards
                  insights={insightsList.map((i) => ({
                    id: i.id,
                    insightText: i.insightText,
                    category: i.category,
                  }))}
                />
              </div>
              <div>
                <HealthScore
                  growthPct={snapshot.growthPct ? Number(snapshot.growthPct) : null}
                  profitMargin={sections.has("profit") ? (metrics.profit_margin ?? null) : null}
                  repeatRate={metrics.repeat_customer_rate ?? null}
                  orders={snapshot.orders ? Number(snapshot.orders) : null}
                />
              </div>
            </div>

            {/* ── Interactive Chat Panel ── */}
            <div>
              <ChatPanel
                businessId={businessId}
                initialMessages={chatHistory.map((m) => ({
                  id: m.id,
                  role: m.role as "user" | "assistant",
                  content: m.content,
                  createdAt: m.createdAt,
                }))}
              />
            </div>
          </>
        )}
      </main>
    </>
  );
}
