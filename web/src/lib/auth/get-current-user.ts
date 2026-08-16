import { auth, currentUser } from "@clerk/nextjs/server";
import { eq } from "drizzle-orm";

import { db } from "@/lib/db";
import { users, type User } from "@/lib/db/schema";

const isPlaceholderKey =
  !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("placeholder") ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("xxxxxxxx");

export async function getCurrentUser(): Promise<User | null> {
  if (isPlaceholderKey) {
    const devClerkId = "dev_user_mock_id";
    const existing = await db.query.users.findFirst({
      where: eq(users.clerkId, devClerkId),
    });
    if (existing) {
      return existing;
    }
    const [created] = await db
      .insert(users)
      .values({
        clerkId: devClerkId,
        email: "owner@mybusiness.com",
        name: "Alex Morgan",
      })
      .returning();
    return created;
  }

  const { userId } = await auth();
  if (!userId) {
    return null;
  }

  const clerkUser = await currentUser();
  if (!clerkUser) {
    return null;
  }

  const email = clerkUser.emailAddresses[0]?.emailAddress;
  if (!email) {
    return null;
  }

  const name =
    [clerkUser.firstName, clerkUser.lastName].filter(Boolean).join(" ") ||
    null;

  const existing = await db.query.users.findFirst({
    where: eq(users.clerkId, userId),
  });

  if (existing) {
    if (existing.email !== email || existing.name !== name) {
      const [updated] = await db
        .update(users)
        .set({ email, name })
        .where(eq(users.id, existing.id))
        .returning();
      return updated;
    }
    return existing;
  }

  const [created] = await db
    .insert(users)
    .values({
      clerkId: userId,
      email,
      name,
    })
    .returning();

  return created;
}
