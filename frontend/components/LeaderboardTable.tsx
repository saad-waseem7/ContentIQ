import { LeaderboardEntry } from "@/lib/api";
import Card from "@/components/Card";
import PlatformIcon from "@/components/PlatformIcon";
import InfoTooltip from "@/components/InfoTooltip";
import { label as humanLabel, formatDate } from "@/lib/labels";

function rankBadgeClasses(rank: number): string {
  if (rank === 1) return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
  if (rank === 2) return "bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-200";
  if (rank === 3) return "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300";
  return "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400";
}

function performanceLabel(z: number): { text: string; classes: string } {
  if (z > 1) return { text: "Strong", classes: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" };
  if (z < -0.5) return { text: "Below avg", classes: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300" };
  return { text: "Average", classes: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300" };
}

export default function LeaderboardTable({ entries }: { entries: LeaderboardEntry[] }) {
  return (
    <Card className="overflow-hidden">
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
              <th className="py-3 px-4 font-medium">
                <span className="flex items-center gap-1">
                  Performance
                  <InfoTooltip text="How far above or below this post scored compared to this creator's own typical post. Higher is better." />
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => {
              const perf = performanceLabel(e.performance_z);
              return (
                <tr key={e.content_id} className="border-b border-slate-100 dark:border-slate-700/60 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/40">
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center justify-center h-6 w-6 rounded-full text-xs font-semibold ${rankBadgeClasses(e.rank)}`}>{e.rank}</span>
                  </td>
                  <td className="py-3 px-4 text-slate-700 dark:text-slate-300">{humanLabel("content_type", e.content_type)}</td>
                  <td className="py-3 px-4">
                    <span className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                      <PlatformIcon platform={e.platform} />
                      {humanLabel("platform", e.platform)}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-700 dark:text-slate-300">{e.hook_type ? humanLabel("hook_type", e.hook_type) : "—"}</td>
                  <td className="py-3 px-4">
                    <div className="flex flex-wrap gap-1">
                      {e.topic_tags.map((t) => (
                        <span key={t} className="bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 text-xs px-2 py-0.5 rounded-full">
                          {humanLabel("topic", t)}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-slate-500 dark:text-slate-400">{formatDate(e.posted_at)}</td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${perf.classes}`}>{perf.text}</span>
                      <span className="text-xs text-slate-400 dark:text-slate-500">{e.performance_z.toFixed(2)}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}