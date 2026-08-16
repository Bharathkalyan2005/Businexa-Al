import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* KPI Cards Skeleton */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="p-5">
            <div className="flex items-center justify-between">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="size-8 rounded-lg" />
            </div>
            <Skeleton className="mt-3 h-8 w-28" />
            <Skeleton className="mt-2 h-3 w-24" />
          </Card>
        ))}
      </div>

      {/* Charts Skeleton */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="h-80 p-6">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="mt-2 h-3 w-48" />
          <Skeleton className="mt-6 h-56 w-full rounded-lg" />
        </Card>
        <Card className="h-80 p-6">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="mt-2 h-3 w-48" />
          <Skeleton className="mt-6 h-56 w-full rounded-lg" />
        </Card>
      </div>

      {/* Bottom sections */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="h-64 p-6 lg:col-span-2">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="mt-4 h-40 w-full rounded-lg" />
        </Card>
        <Card className="h-64 p-6">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="mt-4 h-40 w-full rounded-lg" />
        </Card>
      </div>
    </div>
  );
}
