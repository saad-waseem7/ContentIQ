"use client";

import { useUserId } from "@/lib/UserContext";

export default function UserIdInput() {
  const { userId, setUserId } = useUserId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="user-id" className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
        Viewing as user
      </label>
      <input
        id="user-id"
        type="text"
        value={userId}
        onChange={(e) => setUserId(e.target.value)}
        placeholder="Paste a user ID"
        className="border border-slate-300 dark:border-slate-600 rounded-md px-3 py-1.5 w-full sm:w-72 text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus:border-indigo-500"
      />
    </div>
  );
}