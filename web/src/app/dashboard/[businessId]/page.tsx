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

type DashboardPageProps = PageProps<"/dashboard/[businessId]">;

interface DashboardMetrics {
  average_order_value?: number | null;
  profit_margin?: number | null;
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
            {/* Top KPIs Row */}
            <KpiCards
              revenue={snapshot.revenue ? Number(snapshot.revenue) : null}
              profit={snapshot.profit ? Number(snapshot.profit) : null}
              orders={snapshot.orders ? Number(snapshot.orders) : null}
              aov={metrics.average_order_value ?? null}
              growthPct={snapshot.growthPct ? Number(snapshot.growthPct) : null}
              profitMargin={metrics.profit_margin ?? null}
            />

            {/* Performance Charts Row */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <RevenueChart
                data={metrics.revenue_by_day || metrics.revenue_by_month || []}
              />
              <ProfitChart
                data={metrics.profit_by_day || []}
              />
            </div>

            {/* Top Products and Customer Performance */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <TopProducts products={metrics.top_products || []} />
              <CustomerSection
                customerCount={metrics.customer_count}
                repeatCustomerRate={metrics.repeat_customer_rate}
              />
            </div>

            {/* AI Insights & Health Score */}
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
                  profitMargin={metrics.profit_margin ?? null}
                  repeatRate={metrics.repeat_customer_rate ?? null}
                  orders={snapshot.orders ? Number(snapshot.orders) : null}
                />
              </div>
            </div>

            {/* Interactive Chat Panel */}
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
