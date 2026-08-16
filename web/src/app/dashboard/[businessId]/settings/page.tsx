import { notFound } from "next/navigation";

import { getBusinessForCurrentUser } from "@/actions/business";
import { DashboardHeader } from "@/components/layout/dashboard-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type SettingsPageProps = PageProps<"/dashboard/[businessId]/settings">;

export default async function SettingsPage({ params }: SettingsPageProps) {
  const { businessId } = await params;
  const business = await getBusinessForCurrentUser(businessId);

  if (!business) {
    notFound();
  }

  return (
    <>
      <DashboardHeader
        title="Settings"
        description="Manage your business profile and preferences."
      />
      <main className="flex-1 p-8">
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Business profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <p className="text-muted-foreground">Business name</p>
              <p className="font-medium">{business.name}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Business type</p>
              <p className="font-medium capitalize">
                {business.businessType.replace("_", " ")}
              </p>
            </div>
          </CardContent>
        </Card>
      </main>
    </>
  );
}
