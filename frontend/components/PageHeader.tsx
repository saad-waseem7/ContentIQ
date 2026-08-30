import UserContextSelector from "@/components/UserContextSelector";

export default function PageHeader({
  title, subtitle, helper,
}: { title: string; subtitle?: string; helper?: React.ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-1">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        {helper}
      </div>
      <UserContextSelector />
    </div>
  );
}