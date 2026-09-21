export default function Card({
  children,
  className = "",
  ...rest
}: { children: React.ReactNode; className?: string } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 ${className}`} {...rest}>
      {children}
    </div>
  );
}