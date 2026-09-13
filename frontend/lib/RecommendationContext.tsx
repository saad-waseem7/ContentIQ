"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { RecommendationResponse } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";

interface RecommendationContextValue {
  activeRecommendation: RecommendationResponse | null;
  setActiveRecommendation: (rec: RecommendationResponse, forUserId: string) => void;
  updateActiveRecommendationStatus: (rec: RecommendationResponse) => void;
  clearActiveRecommendation: () => void;
}

const RecommendationContext = createContext<RecommendationContextValue | null>(null);

export function RecommendationProvider({ children }: { children: ReactNode }) {
  const { userId } = useUserId();
  const [activeRecommendation, setActiveRecommendationState] = useState<RecommendationResponse | null>(null);
  const [ownerUserId, setOwnerUserId] = useState<string | null>(null);

  // Leak prevention: if the globally selected user changes away from whoever
  // this recommendation belongs to, clear it — never display one user's
  // recommendation while a different user is selected.
  useEffect(() => {
    if (ownerUserId !== null && userId !== ownerUserId) {
      setActiveRecommendationState(null);
      setOwnerUserId(null);
    }
  }, [userId, ownerUserId]);

  function setActiveRecommendation(rec: RecommendationResponse, forUserId: string) {
    setActiveRecommendationState(rec);
    setOwnerUserId(forUserId);
  }

  function updateActiveRecommendationStatus(rec: RecommendationResponse) {
    setActiveRecommendationState(rec);
  }

  function clearActiveRecommendation() {
    // Display-state only — never calls the API, never touches the
    // persisted recommendations table.
    setActiveRecommendationState(null);
    setOwnerUserId(null);
  }

  return (
    <RecommendationContext.Provider
      value={{ activeRecommendation, setActiveRecommendation, updateActiveRecommendationStatus, clearActiveRecommendation }}
    >
      {children}
    </RecommendationContext.Provider>
  );
}

export function useActiveRecommendation() {
  const ctx = useContext(RecommendationContext);
  if (!ctx) throw new Error("useActiveRecommendation must be used within RecommendationProvider");
  return ctx;
}