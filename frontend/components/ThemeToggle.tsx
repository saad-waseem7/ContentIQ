"use client";
import { useTheme } from "@/lib/ThemeContext";
import { SunIcon, MoonIcon } from "@/components/icons";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      onClick={toggleTheme}
      aria-pressed={theme === "dark"}
      className="flex items-center gap-1.5 h-9 pl-1.5 pr-3 rounded-full border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 transition-colors"
    >
      <span className="flex items-center justify-center h-6 w-6 rounded-full bg-slate-100 dark:bg-slate-700">
        {theme === "dark" ? <MoonIcon /> : <SunIcon />}
      </span>
      {theme === "dark" ? "DARK MODE" : "LIGHT MODE"}
    </button>
  );
}