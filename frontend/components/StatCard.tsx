export default function StatCard({ label, value, sublabel }: { label: string; value: string; sublabel?: string }) {
  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 p-4">
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</p>
      <p className="text-base font-semibold text-slate-900 dark:text-slate-100 mt-1 truncate">{value}</p>
      {sublabel && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{sublabel}</p>}
    </div>
  );
}