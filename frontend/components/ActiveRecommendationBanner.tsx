"use client";

import { useState } from "react";
import { useActiveRecommendation } from "@/lib/RecommendationContext";
import { submitFeedback, ApiError } from "@/lib/api";
import RecommendationCard from "@/components/RecommendationCard";
import { messageForStatus } from "@/components/StatusMessage";

export default function ActiveRecommendationBanner() {
  const { activeRecommendation, updateActiveRecommendationStatus, clearActiveRecommendation } = useActiveRecommendation();
  const [feedbackPending, setFeedbackPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!activeRecommendation) return null;

  function handleFeedback(status: "actioned" | "dismissed") {
    setFeedbackPending(true);
    setError(null);
    submitFeedback(activeRecommendation!.id, status)
      .then(updateActiveRecommendationStatus)
      .catch((e) => setError(e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server."))
      .finally(() => setFeedbackPending(false));
  }

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Active recommendation</span>
        <button
          onClick={clearActiveRecommendation}
          className="text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
        >
          Clear
        </button>
      </div>
      {error && <p className="text-sm text-rose-600 dark:text-rose-400 mb-2" role="alert">{error}</p>}
      <RecommendationCard rec={activeRecommendation} onFeedback={handleFeedback} feedbackPending={feedbackPending} />
    </div>
  );
}