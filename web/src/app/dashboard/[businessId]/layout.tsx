import { notFound } from "next/navigation";
import type { Metadata } from "next";

import { getBusinessForCurrentUser } from "@/actions/business";
import { Sidebar } from "@/components/layout/sidebar";

type DashboardLayoutProps = LayoutProps<"/dashboard/[businessId]">;

export default async function DashboardLayout({
  children,
  params,
}: DashboardLayoutProps) {
  const { businessId } = await params;
  const business = await getBusinessForCurrentUser(businessId);

  if (!business) {
    notFound();
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar businessId={businessId} businessName={business.name} />
      <div className="flex flex-1 flex-col overflow-y-auto">{children}</div>
    </div>
  );
}

export async function generateMetadata({
  params,
}: DashboardLayoutProps): Promise<Metadata> {
  const { businessId } = await params;
  const business = await getBusinessForCurrentUser(businessId);

  return {
    title: business ? `${business.name} | Businexa AI` : "Dashboard | Businexa AI",
  };
}
