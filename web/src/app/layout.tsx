import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Businexa AI",
  description: "AI-powered business analytics for small business owners",
};

const isPlaceholderKey =
  !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("placeholder") ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("xxxxxxxx");

export default function RootLayout({ children }: LayoutProps<"/">) {
  const content = (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );

  if (isPlaceholderKey) {
    return content;
  }

  return <ClerkProvider>{content}</ClerkProvider>;
}
