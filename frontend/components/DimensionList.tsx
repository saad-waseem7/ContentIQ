import { DimensionEntry } from "@/lib/api";
import { label as humanLabel, describePerformance } from "@/lib/labels";

export default function DimensionList({ title, dimension, entries }: { title: string; dimension: string; entries: DimensionEntry[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">{title}</h3>
      {entries.length === 0 ? (
        <p className="text-xs text-slate-400 dark:text-slate-500">Not enough data yet to compare.</p>
      ) : (
        <ul className="space-y-3">
          {entries.map((e) => {
            const perf = describePerformance(e.mean_performance_z, e.n);
            const color =
              perf.direction === "above" ? "text-emerald-600 dark:text-emerald-400" :
              perf.direction === "below" ? "text-rose-600 dark:text-rose-400" :
              "text-slate-500 dark:text-slate-400";
            return (
              <li key={e.value} className="border-b border-slate-100 dark:border-slate-700/60 last:border-0 pb-3 last:pb-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{humanLabel(dimension, e.value)}</span>
                  {e.is_standout && (
                    <span className="text-[10px] font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 px-1.5 py-0.5 rounded-full">
                      standout
                    </span>
                  )}
                </div>
                <p className={`text-xs ${color}`}>{perf.sdLine}</p>
                <p className="text-xs text-slate-400 dark:text-slate-500">{perf.postsLine}</p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}