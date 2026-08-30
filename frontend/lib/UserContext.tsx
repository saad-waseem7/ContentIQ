"use client";

import { createContext, useContext, useState, ReactNode } from "react";

const UserContext = createContext<{ userId: string; setUserId: (id: string) => void } | null>(null);

export function UserProvider({ children, initialUserId }: { children: ReactNode; initialUserId?: string }) {
  const [userId, setUserId] = useState(initialUserId ?? process.env.NEXT_PUBLIC_DEFAULT_USER_ID ?? "");
  return <UserContext.Provider value={{ userId, setUserId }}>{children}</UserContext.Provider>;
}

export function useUserId() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUserId must be used within UserProvider");
  return ctx;
}