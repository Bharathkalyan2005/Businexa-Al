import { redirect } from "next/navigation";

import { getBusinessesForCurrentUser } from "@/actions/business";

export const dynamic = "force-dynamic";

export default async function DashboardIndexPage() {
  const businesses = await getBusinessesForCurrentUser();

  if (businesses.length === 0) {
    redirect("/create-business");
  }

  redirect(`/dashboard/${businesses[0].id}`);
}
