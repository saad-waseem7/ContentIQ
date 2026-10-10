"use client";
import { useUserId } from "@/lib/UserContext";

export default function UserContextSelector() {
  const { userId, setUserId } = useUserId();
  return (
    <div className="flex flex-col gap-1 sm:items-end shrink-0">
      <label htmlFor="user-context" className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
        Viewing user
      </label>
      <input
        id="user-context"
        type="text"
        value={userId}
        onChange={(e) => setUserId(e.target.value.trim())}
        placeholder="Paste a user ID"
        className="h-9 border border-slate-300 dark:border-slate-600 rounded-md px-3 text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus:border-indigo-500 w-full sm:w-64"
      />
    </div>
  );
}