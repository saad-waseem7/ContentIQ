import { DimensionEntry } from "@/lib/api";

export default function DimensionList({ title, entries }: { title: string; entries: DimensionEntry[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">{title}</h3>
      {entries.length === 0 ? (
        <p className="text-xs text-slate-400 dark:text-slate-500">Not enough data yet to compare.</p>
      ) : (
        <ul className="space-y-1.5">
          {entries.map((e) => (
            <li key={e.value} className="flex items-center justify-between text-sm">
              <span className="text-slate-700 dark:text-slate-300">{e.value}</span>
              <span className="flex items-center gap-2">
                {e.is_standout && (
                  <span className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 px-1.5 py-0.5 rounded-full">
                    standout
                  </span>
                )}
                <span className="text-slate-400 dark:text-slate-500 text-xs">{e.mean_performance_z.toFixed(2)} · n={e.n}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}