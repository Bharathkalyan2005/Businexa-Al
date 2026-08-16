"use server";

import { and, eq } from "drizzle-orm";
import { revalidatePath } from "next/cache";

import { getCurrentUser } from "@/lib/auth/get-current-user";
import { db } from "@/lib/db";
import { businesses, chatMessages } from "@/lib/db/schema";
import { sendChatMessage as apiSendChatMessage } from "@/lib/api/python-client";

export async function getChatMessages(businessId: string) {
  const user = await getCurrentUser();
  if (!user) return [];

  const business = await db.query.businesses.findFirst({
    where: and(eq(businesses.id, businessId), eq(businesses.userId, user.id)),
  });
  if (!business) return [];

  return db.query.chatMessages.findMany({
    where: eq(chatMessages.businessId, businessId),
    orderBy: [chatMessages.createdAt],
  });
}

export async function askBusinessQuestion(businessId: string, question: string) {
  const user = await getCurrentUser();
  if (!user) return { error: "Unauthorized" };

  const business = await db.query.businesses.findFirst({
    where: and(eq(businesses.id, businessId), eq(businesses.userId, user.id)),
  });
  if (!business) return { error: "Business not found" };

  if (!question.trim()) {
    return { error: "Question cannot be empty" };
  }

  try {
    const res = await apiSendChatMessage(businessId, question.trim());
    revalidatePath(`/dashboard/${businessId}`);
    return { answer: res.answer };
  } catch (error) {
    console.error("Chat error:", error);
    return { error: error instanceof Error ? error.message : "Failed to get AI answer" };
  }
}
