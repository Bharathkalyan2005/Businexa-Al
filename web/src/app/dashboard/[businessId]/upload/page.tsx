import { notFound } from "next/navigation";

import { getBusinessForCurrentUser } from "@/actions/business";
import { getDatasetsForBusiness } from "@/actions/datasets";
import { DashboardHeader } from "@/components/layout/dashboard-header";
import { UploadSection } from "@/components/upload/upload-section";

type UploadPageProps = PageProps<"/dashboard/[businessId]/upload">;

export default async function UploadPage({ params }: UploadPageProps) {
  const { businessId } = await params;
  const business = await getBusinessForCurrentUser(businessId);

  if (!business) {
    notFound();
  }

  const existingDatasets = await getDatasetsForBusiness(businessId);

  return (
    <>
      <DashboardHeader
        title="Upload"
        description="Upload sales data to analyze your business performance."
      />
      <main className="flex-1 p-8">
        <div className="mx-auto max-w-3xl space-y-8">
          <UploadSection
            businessId={businessId}
            existingDatasets={existingDatasets}
          />
        </div>
      </main>
    </>
  );
}
