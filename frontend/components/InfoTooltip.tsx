export default function InfoTooltip({ text }: { text: string }) {
  return (
    <span
      title={text}
      tabIndex={0}
      aria-label={text}
      className="inline-flex items-center justify-center h-4 w-4 rounded-full border border-slate-300 dark:border-slate-600 text-slate-400 dark:text-slate-500 text-[10px] cursor-help focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 shrink-0"
    >
      i
    </span>
  );
}