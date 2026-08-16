import { redirect } from "next/navigation";

import { getBusinessesForCurrentUser } from "@/actions/business";
import { CreateBusinessForm } from "@/components/create-business-form";

export const dynamic = "force-dynamic";

export default async function CreateBusinessPage() {
  const businesses = await getBusinessesForCurrentUser();

  if (businesses.length > 0) {
    redirect(`/dashboard/${businesses[0].id}`);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4 py-12">
      <CreateBusinessForm />
    </div>
  );
}
