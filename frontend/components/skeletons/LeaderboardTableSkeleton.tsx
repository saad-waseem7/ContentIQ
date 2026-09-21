import Card from "@/components/Card";
import Skeleton from "@/components/skeletons/Skeleton";

export default function LeaderboardTableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <Card role="status" aria-label="Loading leaderboard" aria-busy="true" className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wide">
              <th className="py-3 px-4 font-medium">Rank</th>
              <th className="py-3 px-4 font-medium">Content Type</th>
              <th className="py-3 px-4 font-medium">Platform</th>
              <th className="py-3 px-4 font-medium">Hook</th>
              <th className="py-3 px-4 font-medium">Topics</th>
              <th className="py-3 px-4 font-medium">Posted</th>
              <th className="py-3 px-4 font-medium">Performance</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rows }).map((_, i) => (
              <tr key={i} className="border-b border-slate-100 dark:border-slate-700/60 last:border-0">
                <td className="py-3 px-4"><Skeleton className="h-6 w-6 rounded-full" /></td>
                <td className="py-3 px-4"><Skeleton className="h-4 w-20" /></td>
                <td className="py-3 px-4"><Skeleton className="h-4 w-24" /></td>
                <td className="py-3 px-4"><Skeleton className="h-4 w-16" /></td>
                <td className="py-3 px-4"><Skeleton className="h-5 w-20 rounded-full" /></td>
                <td className="py-3 px-4"><Skeleton className="h-4 w-16" /></td>
                <td className="py-3 px-4"><Skeleton className="h-5 w-24 rounded-full" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}