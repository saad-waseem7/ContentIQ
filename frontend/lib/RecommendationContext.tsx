"use client";

import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react";
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
  // Latest selected user, readable from callbacks that outlive the render that created them.
  const userIdRef = useRef(userId);
  userIdRef.current = userId;

  // Drop the active card when the selected user no longer owns it.
  useEffect(() => {
    if (ownerUserId !== null && userId !== ownerUserId) {
      setActiveRecommendationState(null);
      setOwnerUserId(null);
    }
  }, [userId, ownerUserId]);

  function setActiveRecommendation(rec: RecommendationResponse, forUserId: string) {
    // A response that arrives after the user switched must not be shown for the new user.
    if (forUserId !== userIdRef.current) return;
    setActiveRecommendationState(rec);
    setOwnerUserId(forUserId);
  }

  function updateActiveRecommendationStatus(rec: RecommendationResponse) {
    // Only update the recommendation that is still on screen; a late feedback response
    // must not bring back one that was cleared or belongs to a previously selected user.
    setActiveRecommendationState((current) => (current && current.id === rec.id ? rec : current));
  }

  function clearActiveRecommendation() {
    // Clearing this card affects display state only; the saved recommendation remains unchanged.
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