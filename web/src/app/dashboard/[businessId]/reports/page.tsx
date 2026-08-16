import { notFound } from "next/navigation";

import { getBusinessForCurrentUser } from "@/actions/business";
import { getReportsForBusiness } from "@/actions/reports";
import { DashboardHeader } from "@/components/layout/dashboard-header";
import { GenerateButton } from "@/components/reports/generate-button";
import { ReportList } from "@/components/reports/report-list";

type ReportsPageProps = PageProps<"/dashboard/[businessId]/reports">;

export default async function ReportsPage({ params }: ReportsPageProps) {
  const { businessId } = await params;
  const business = await getBusinessForCurrentUser(businessId);

  if (!business) {
    notFound();
  }

  const reports = await getReportsForBusiness(businessId);

  return (
    <>
      <DashboardHeader
        title="Reports"
        description={`Executive summaries and downloadable PDF documentation for ${business.name}.`}
      />
      <main className="flex-1 space-y-6 p-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Business Reports</h2>
            <p className="text-sm text-muted-foreground">
              Automated multi-page PDFs ready for stakeholders and management.
            </p>
          </div>
          <GenerateButton businessId={businessId} />
        </div>

        <ReportList reports={reports} />
      </main>
    </>
  );
}
