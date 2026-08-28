"use client";

import { Inter } from "next/font/google";
import Link from "next/link";
import { usePathname } from "next/navigation";
import "./globals.css";
import { UserProvider } from "@/lib/UserContext";
import UserIdInput from "@/components/UserIdInput";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const active = pathname?.startsWith(href);
  return (
    <Link
      href={href}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
        active ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
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
      </head>
      <body className="bg-slate-50 text-slate-900 min-h-screen font-sans">
        <UserProvider>
          <div className="max-w-5xl mx-auto px-4 sm:px-6">
            <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 py-5 border-b border-slate-200">
              <div className="flex items-center gap-6">
                <span className="text-base font-semibold tracking-tight text-slate-900">ContentIQ</span>
                <nav className="flex gap-1">
                  <NavLink href="/leaderboard">Leaderboard</NavLink>
                  <NavLink href="/recommend">Daily recommendation</NavLink>
                  <NavLink href="/insights">Insights</NavLink>
                </nav>
              </div>
              <UserIdInput />
            </header>
            <main className="py-8">{children}</main>
          </div>
        </UserProvider>
      </body>
    </html>
  );
}