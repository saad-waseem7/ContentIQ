"use client";

import Link from "next/link";
import "./globals.css";
import { UserProvider } from "@/lib/UserContext";
import UserIdInput from "@/components/UserIdInput";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="max-w-4xl mx-auto p-6">
        <UserProvider>
          <div className="flex justify-between items-center mb-6 border-b border-gray-200 pb-4">
            <nav className="flex gap-4 text-sm font-medium">
              <Link href="/leaderboard">Leaderboard</Link>
              <Link href="/recommend">Daily recommendation</Link>
            </nav>
            <UserIdInput />
          </div>
          {children}
        </UserProvider>
      </body>
    </html>
  );
}