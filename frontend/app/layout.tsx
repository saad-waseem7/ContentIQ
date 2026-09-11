"use client";

import { Inter } from "next/font/google";
import Link from "next/link";
import { usePathname } from "next/navigation";
import "./globals.css";
import { UserProvider } from "@/lib/UserContext";
import { ThemeProvider } from "@/lib/ThemeContext";
import { themeInitScript } from "@/lib/theme";
import ThemeToggle from "@/components/ThemeToggle";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const active = pathname?.startsWith(href);
  return (
    <Link
      href={href}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
        active
          ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800"
      }`}
    >
      {children}
    </Link>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        <title>ContentIQ</title>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 min-h-screen font-sans transition-colors">
        <ThemeProvider>
          <UserProvider>
            <div className="max-w-5xl mx-auto px-4 sm:px-6">
              <header className="flex items-center justify-between gap-3 py-5 border-b border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-6">
                  <span className="text-base font-semibold tracking-tight text-slate-900 dark:text-slate-100">ContentIQ</span>
                  <nav className="flex gap-1">
                    <NavLink href="/leaderboard">Leaderboard</NavLink>
                    <NavLink href="/recommend">Daily Recommendation</NavLink>
                    <NavLink href="/insights">Insights</NavLink>
                    <NavLink href="/history">History</NavLink>
                  </nav>
                </div>
                <ThemeToggle />
              </header>
              <main className="py-8">{children}</main>
            </div>
          </UserProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}