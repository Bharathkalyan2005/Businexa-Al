"use server";

import { and, desc, eq } from "drizzle-orm";

import { getCurrentUser } from "@/lib/auth/get-current-user";
import { db } from "@/lib/db";
import {
  businesses,
  chatMessages,
  datasets,
  insights,
  metricsSnapshots,
} from "@/lib/db/schema";

export async function getDashboardData(businessId: string) {
  const user = await getCurrentUser();
  if (!user) return null;

  // Verify business ownership
  const business = await db.query.businesses.findFirst({
    where: and(eq(businesses.id, businessId), eq(businesses.userId, user.id)),
  });
  if (!business) return null;

  // Get latest dataset
  const latestDataset = await db.query.datasets.findFirst({
    where: eq(datasets.businessId, businessId),
    orderBy: [desc(datasets.uploadedAt)],
  });

  if (!latestDataset) {
    return {
      business,
      dataset: null,
      snapshot: null,
      insightsList: [],
      chatHistory: [],
    };
  }

  // Get latest metrics snapshot
  const snapshot = await db.query.metricsSnapshots.findFirst({
    where: eq(metricsSnapshots.datasetId, latestDataset.id),
    orderBy: [desc(metricsSnapshots.computedAt)],
  });

  // Get latest insights
  const insightsList = await db.query.insights.findMany({
    where: eq(insights.datasetId, latestDataset.id),
    orderBy: [desc(insights.createdAt)],
  });

  // Get chat messages
  const chatHistory = await db.query.chatMessages.findMany({
    where: eq(chatMessages.businessId, businessId),
    orderBy: [chatMessages.createdAt],
  });

  return {
    business,
    dataset: latestDataset,
    snapshot: snapshot
      ? {
          ...snapshot,
          rawJson: snapshot.rawJson as Record<string, unknown>,
        }
      : null,
    insightsList,
    chatHistory,
  };
}
