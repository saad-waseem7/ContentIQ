import { LeaderboardEntry } from "@/lib/api";

function rankBadgeClasses(rank: number): string {
  if (rank === 1) return "bg-amber-100 text-amber-800";
  if (rank === 2) return "bg-slate-200 text-slate-700";
  if (rank === 3) return "bg-orange-100 text-orange-800";
  return "bg-slate-100 text-slate-500";
}

function performanceLabel(z: number): { text: string; classes: string } {
  if (z > 1) return { text: "Strong", classes: "bg-emerald-100 text-emerald-700" };
  if (z < -0.5) return { text: "Below avg", classes: "bg-rose-100 text-rose-700" };
  return { text: "Average", classes: "bg-slate-100 text-slate-600" };
}

export default function LeaderboardTable({ entries }: { entries: LeaderboardEntry[] }) {
  return (
    <div className="border border-slate-200 rounded-lg bg-white overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b border-slate-200 bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
              <th className="py-3 px-4 font-medium">Rank</th>
              <th className="py-3 px-4 font-medium">Type</th>
              <th className="py-3 px-4 font-medium">Platform</th>
              <th className="py-3 px-4 font-medium">Hook</th>
              <th className="py-3 px-4 font-medium">Topics</th>
              <th className="py-3 px-4 font-medium">Posted</th>
              <th className="py-3 px-4 font-medium">Performance</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => {
              const perf = performanceLabel(e.performance_z);
              return (
                <tr key={e.content_id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center justify-center h-6 w-6 rounded-full text-xs font-semibold ${rankBadgeClasses(e.rank)}`}>
                      {e.rank}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-700">{e.content_type}</td>
                  <td className="py-3 px-4 text-slate-700">{e.platform}</td>
                  <td className="py-3 px-4 text-slate-700">{e.hook_type ?? "—"}</td>
                  <td className="py-3 px-4">
                    <div className="flex flex-wrap gap-1">
                      {e.topic_tags.map((t) => (
                        <span key={t} className="bg-indigo-50 text-indigo-700 text-xs px-2 py-0.5 rounded-full">
                          {t}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-slate-500">{new Date(e.posted_at).toLocaleDateString()}</td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${perf.classes}`}>{perf.text}</span>
                      <span className="text-xs text-slate-400">({e.performance_z.toFixed(2)})</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}