import { UserButton } from "@clerk/nextjs";
import { User } from "lucide-react";

type DashboardHeaderProps = {
  title: string;
  description?: string;
};

const isPlaceholderKey =
  !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("placeholder") ||
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("xxxxxxxx");

export function DashboardHeader({ title, description }: DashboardHeaderProps) {
  return (
    <header className="flex items-start justify-between border-b border-border bg-background px-8 py-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {isPlaceholderKey ? (
        <div className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
          <User className="size-4" />
        </div>
      ) : (
        <UserButton />
      )}
    </header>
  );
}
