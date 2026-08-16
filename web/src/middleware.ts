import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { type NextRequest, NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher(["/sign-in(.*)", "/sign-up(.*)"]);

const isPlaceholderKey =
  !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("placeholder") ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("xxxxxxxx");

// When real Clerk keys are provided, use Clerk's middleware auth guard.
// Otherwise, allow local development preview without crashing on key format validation.
const customMiddleware = isPlaceholderKey
  ? function devMiddleware(_request: NextRequest) {
      return NextResponse.next();
    }
  : clerkMiddleware(async (auth, request) => {
      if (!isPublicRoute(request)) {
        await auth.protect();
      }
    });

export default customMiddleware;

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
