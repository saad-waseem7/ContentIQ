import Card from "@/components/Card";
import Skeleton from "@/components/skeletons/Skeleton";

export default function RecommendationCardSkeleton() {
  return (
    <Card role="status" aria-label="Generating recommendation" aria-busy="true" className="p-6 max-w-xl shadow-sm">
      <div className="flex justify-between items-start mb-4">
        <Skeleton className="h-6 w-20 rounded" />
        <div className="flex flex-col items-end gap-2">
          <Skeleton className="h-7 w-14" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
      </div>
      <div className="space-y-2 mb-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-2/3" />
      </div>
      <Skeleton className="h-4 w-40 mb-3" />
      <div className="bg-slate-50 dark:bg-slate-900/60 border-l-2 border-indigo-300 dark:border-indigo-500 rounded-r px-4 py-3 mb-5">
        <Skeleton className="h-4 w-full mb-1.5" />
        <Skeleton className="h-4 w-3/4" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-9 w-28 rounded-md" />
        <Skeleton className="h-9 w-20 rounded-md" />
        <Skeleton className="h-9 w-16 rounded-md" />
      </div>
    </Card>
  );
}