export function LoadingMessage({ text = "Loading..." }: { text?: string }) {
  return <p className="text-gray-500 text-sm py-4">{text}</p>;
}

export function EmptyMessage({ text }: { text: string }) {
  return <p className="text-gray-500 text-sm py-4">{text}</p>;
}

export function ErrorMessage({ text }: { text: string }) {
  return <p className="text-red-600 text-sm py-4" role="alert">{text}</p>;
}

// Maps ApiError status codes to the specific messages decided in planning —
// no generic "something went wrong" catch-all.
export function messageForStatus(status: number, detail: string): string {
  if (status === 404) return "No data for this user ID.";
  if (status === 503) return "Backend data isn't built yet — run the pipeline scripts.";
  if (status === 502) return "Couldn't generate a recommendation. Try again.";
  if (status === 422) return detail;
  return `Request failed: ${detail}`;
}