"use server";

import { and, desc, eq } from "drizzle-orm";
import { revalidatePath } from "next/cache";

import { getCurrentUser } from "@/lib/auth/get-current-user";
import { db } from "@/lib/db";
import { businesses, datasets, reports } from "@/lib/db/schema";
import { generatePdfReport as apiGeneratePdfReport } from "@/lib/api/python-client";

export async function getReportsForBusiness(businessId: string) {
  const user = await getCurrentUser();
  if (!user) return [];

  const business = await db.query.businesses.findFirst({
    where: and(eq(businesses.id, businessId), eq(businesses.userId, user.id)),
  });
  if (!business) return [];

  return db.query.reports.findMany({
    where: eq(reports.businessId, businessId),
    orderBy: [desc(reports.generatedAt)],
    with: {
      dataset: true,
    },
  });
}

export async function triggerReportGeneration(businessId: string) {
  const user = await getCurrentUser();
  if (!user) return { error: "Unauthorized" };

  const business = await db.query.businesses.findFirst({
    where: and(eq(businesses.id, businessId), eq(businesses.userId, user.id)),
  });
  if (!business) return { error: "Business not found" };

  // Get latest dataset
  const latestDataset = await db.query.datasets.findFirst({
    where: eq(datasets.businessId, businessId),
    orderBy: [desc(datasets.uploadedAt)],
  });

  if (!latestDataset) {
    return { error: "No datasets found. Please upload a dataset first." };
  }

  try {
    const res = await apiGeneratePdfReport(businessId, latestDataset.id);
    revalidatePath(`/dashboard/${businessId}/reports`);
    return { success: true, report: res };
  } catch (error) {
    console.error("Report generation error:", error);
    return { error: error instanceof Error ? error.message : "Failed to generate PDF report" };
  }
}
