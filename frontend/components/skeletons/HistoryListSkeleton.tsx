import Card from "@/components/Card";
import Skeleton from "@/components/skeletons/Skeleton";

export default function HistoryListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Card role="status" aria-label="Loading recommendation history" aria-busy="true" className="overflow-hidden">
      <ul>
        {Array.from({ length: rows }).map((_, i) => (
          <li key={i} className="border-b border-slate-100 dark:border-slate-700/60 last:border-0 px-5 py-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <Skeleton className="h-3 w-24 mb-2" />
                <Skeleton className="h-4 w-3/4" />
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <Skeleton className="h-4 w-10" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}