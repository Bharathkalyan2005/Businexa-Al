"use server";

import { and, asc, eq } from "drizzle-orm";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/lib/auth/get-current-user";
import { isBusinessType } from "@/lib/constants";
import { db } from "@/lib/db";
import { businesses, type Business } from "@/lib/db/schema";

export async function createBusiness(formData: FormData): Promise<{ error?: string }> {
  const user = await getCurrentUser();
  if (!user) {
    return { error: "You must be signed in to create a business." };
  }

  const name = formData.get("name");
  const businessType = formData.get("businessType");

  if (typeof name !== "string" || name.trim().length === 0) {
    return { error: "Business name is required." };
  }

  if (typeof businessType !== "string" || !isBusinessType(businessType)) {
    return { error: "Please select a valid business type." };
  }

  const [business] = await db
    .insert(businesses)
    .values({
      userId: user.id,
      name: name.trim(),
      businessType,
    })
    .returning();

  redirect(`/dashboard/${business.id}`);
}

export async function getBusinessesForCurrentUser(): Promise<Business[]> {
  const user = await getCurrentUser();
  if (!user) {
    return [];
  }

  return db.query.businesses.findMany({
    where: eq(businesses.userId, user.id),
    orderBy: [asc(businesses.createdAt)],
  });
}

export async function getBusinessForCurrentUser(
  businessId: string,
): Promise<Business | null> {
  const user = await getCurrentUser();
  if (!user) {
    return null;
  }

  const business = await db.query.businesses.findFirst({
    where: and(eq(businesses.id, businessId), eq(businesses.userId, user.id)),
  });

  return business ?? null;
}
