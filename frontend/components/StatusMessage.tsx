import { AlertIcon, InboxIcon, SpinnerIcon } from "@/components/icons";

export function LoadingMessage({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="flex items-center gap-3 border border-slate-200 rounded-lg bg-white px-5 py-8 justify-center">
      <SpinnerIcon />
      <p className="text-sm text-slate-500">{text}</p>
    </div>
  );
}

export function EmptyMessage({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center gap-2 border border-dashed border-slate-300 rounded-lg bg-white px-5 py-10 text-center">
      <InboxIcon />
      <p className="text-sm text-slate-500 max-w-xs">{text}</p>
    </div>
  );
}

export function ErrorMessage({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-3 border border-rose-200 rounded-lg bg-rose-50 px-4 py-3" role="alert">
      <AlertIcon />
      <p className="text-sm text-rose-700">{text}</p>
    </div>
  );
}

export function messageForStatus(status: number, detail: string): string {
  if (status === 404) return "No data for this user ID.";
  if (status === 503) return "Backend data isn't built yet — run the pipeline scripts.";
  if (status === 502) return "Couldn't generate a recommendation. Try again.";
  if (status === 422) return detail;
  return `Request failed: ${detail}`;
}