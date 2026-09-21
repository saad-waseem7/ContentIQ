import Card from "@/components/Card";
import Skeleton from "@/components/skeletons/Skeleton";

function StatCardSkeleton() {
  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 p-4">
      <Skeleton className="h-3 w-24 mb-2" />
      <Skeleton className="h-5 w-20 mb-2" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

function DimensionListSkeleton() {
  return (
    <div>
      <Skeleton className="h-4 w-24 mb-3" />
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i}>
            <Skeleton className="h-4 w-28 mb-1" />
            <Skeleton className="h-3 w-32 mb-1" />
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}

function SectionSkeleton({ titleWidth, children }: { titleWidth: string; children: React.ReactNode }) {
  return (
    <Card className="p-5 mb-5">
      <Skeleton className={`h-4 ${titleWidth} mb-1`} />
      <Skeleton className="h-3 w-64 mb-4" />
      {children}
    </Card>
  );
}

export default function InsightsPageSkeleton() {
  return (
    <div role="status" aria-label="Loading insights" aria-busy="true">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
      </div>

      <SectionSkeleton titleWidth="w-40">
        <div className="grid sm:grid-cols-2 gap-6">
          {Array.from({ length: 4 }).map((_, i) => <DimensionListSkeleton key={i} />)}
        </div>
      </SectionSkeleton>

      <SectionSkeleton titleWidth="w-48">
        <Skeleton className="h-56 w-full" />
      </SectionSkeleton>

      <SectionSkeleton titleWidth="w-36">
        <Skeleton className="h-4 w-64 mb-3" />
        <Skeleton className="h-56 w-full" />
      </SectionSkeleton>

      <SectionSkeleton titleWidth="w-44">
        <Skeleton className="h-4 w-full" />
      </SectionSkeleton>

      <SectionSkeleton titleWidth="w-52">
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex justify-between">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
          ))}
        </div>
      </SectionSkeleton>

      <SectionSkeleton titleWidth="w-32">
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14 w-full rounded" />)}
        </div>
      </SectionSkeleton>
    </div>
  );
}