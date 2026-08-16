import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

const isPlaceholderKey =
  !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("placeholder") ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("xxxxxxxx");

export default async function HomePage() {
  if (isPlaceholderKey) {
    redirect("/dashboard");
  }

  const { userId } = await auth();

  if (userId) {
    redirect("/dashboard");
  }

  redirect("/sign-in");
}
