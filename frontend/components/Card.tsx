export default function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 ${className}`}>
      {children}
    </div>
  );
}