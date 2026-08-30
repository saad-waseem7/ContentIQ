const STYLES: Record<string, string> = {
  youtube: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  youtube_shorts: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  instagram: "bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300",
  tiktok: "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
  x: "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
  linkedin: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
};
const LETTERS: Record<string, string> = {
  youtube: "YT", youtube_shorts: "YT", instagram: "IG", tiktok: "TT", x: "X", linkedin: "IN",
};

export default function PlatformIcon({ platform }: { platform: string }) {
  return (
    <span className={`inline-flex items-center justify-center h-5 w-5 rounded text-[9px] font-bold ${STYLES[platform] ?? "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400"}`}>
      {LETTERS[platform] ?? "?"}
    </span>
  );
}