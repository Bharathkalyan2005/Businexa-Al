"use server";

import { and, desc, eq } from "drizzle-orm";

import { getCurrentUser } from "@/lib/auth/get-current-user";
import { db } from "@/lib/db";
import { businesses, datasets } from "@/lib/db/schema";

export type DatasetWithColumns = {
  id: string;
  businessId: string;
  filename: string;
  storageUrl: string;
  status: string;
  uploadedAt: Date;
  columns: {
    id: string;
    columnName: string;
    detectedType: string;
    missingCount: string | null;
    missingPct: string | null;
  }[];
};

export async function getDatasetsForBusiness(
  businessId: string,
): Promise<DatasetWithColumns[]> {
  const user = await getCurrentUser();
  if (!user) return [];

  // Verify business ownership
  const business = await db.query.businesses.findFirst({
    where: and(eq(businesses.id, businessId), eq(businesses.userId, user.id)),
  });
  if (!business) return [];

  const allDatasets = await db.query.datasets.findMany({
    where: eq(datasets.businessId, businessId),
    orderBy: [desc(datasets.uploadedAt)],
    with: {
      columns: true,
    },
  });

  return allDatasets.map((d) => ({
    id: d.id,
    businessId: d.businessId,
    filename: d.filename,
    storageUrl: d.storageUrl,
    status: d.status,
    uploadedAt: d.uploadedAt,
    columns: d.columns.map((c) => ({
      id: c.id,
      columnName: c.columnName,
      detectedType: c.detectedType,
      missingCount: c.missingCount,
      missingPct: c.missingPct,
    })),
  }));
}

export async function getLatestDataset(
  businessId: string,
): Promise<DatasetWithColumns | null> {
  const results = await getDatasetsForBusiness(businessId);
  return results[0] ?? null;
}
