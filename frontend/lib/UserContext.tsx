"use client";

import { createContext, useContext, useState, ReactNode } from "react";

// Deliberately NOT an auth system. PRD §11 stubs auth for MVP, but the
// seeded dataset has multiple users (45, per the Week 2 generator) and
// there's no session to derive identity from. This is a plain, swappable
// placeholder — replace with real session-derived identity when auth exists,
// with no changes needed to the pages/components that consume useUserId().
const UserContext = createContext<{ userId: string; setUserId: (id: string) => void } | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState(process.env.NEXT_PUBLIC_DEFAULT_USER_ID || "");
  return <UserContext.Provider value={{ userId, setUserId }}>{children}</UserContext.Provider>;
}

export function useUserId() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUserId must be used within UserProvider");
  return ctx;
}