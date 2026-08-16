import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4">
      <h1 className="text-2xl font-semibold">Business not found</h1>
      <p className="text-sm text-muted-foreground">
        This business does not exist or you do not have access to it.
      </p>
      <Link href="/dashboard">
        <Button variant="outline">Back to dashboard</Button>
      </Link>
    </div>
  );
}
