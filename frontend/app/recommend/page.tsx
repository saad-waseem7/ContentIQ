"use client";

import { useState } from "react";
import { generateRecommendation, submitFeedback, ApiError } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";
import { useActiveRecommendation } from "@/lib/RecommendationContext";
import { LoadingMessage, ErrorMessage, EmptyMessage, messageForStatus } from "@/components/StatusMessage";
import PageHeader from "@/components/PageHeader";
import RecommendationCard from "@/components/RecommendationCard";
import TryYourIdeaPanel from "@/components/TryYourIdeaPanel";

export default function RecommendPage() {
  const { userId } = useUserId();
  const { activeRecommendation, setActiveRecommendation, updateActiveRecommendationStatus, clearActiveRecommendation } = useActiveRecommendation();
  const [loading, setLoading] = useState(false);
  const [feedbackPending, setFeedbackPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleGenerate() {
    if (!userId) return;
    setLoading(true);
    setError(null);
    generateRecommendation(userId)
      .then((rec) => setActiveRecommendation(rec, userId))
      .catch((e) => setError(e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server."))
      .finally(() => setLoading(false));
  }

  function handleFeedback(status: "actioned" | "dismissed") {
    if (!activeRecommendation) return;
    setFeedbackPending(true);
    setError(null);
    submitFeedback(activeRecommendation.id, status)
      .then(updateActiveRecommendationStatus)
      .catch((e) => setError(e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server."))
      .finally(() => setFeedbackPending(false));
  }

  return (
    <div>
      <PageHeader title="Daily Recommendation" subtitle="A grounded content idea, scored against this creator's own performance model." />

      {!userId && <EmptyMessage text="Enter a user ID above to generate a recommendation." />}

      {userId && (
        <>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="h-9 px-4 bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-400 text-white rounded-md text-sm font-medium disabled:opacity-50 mb-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 transition-colors"
          >
            {loading ? "Generating..." : "Generate Recommendation"}
          </button>
          {loading && <LoadingMessage text="Generating Recommendation..." />}
          {!loading && error && <ErrorMessage text={error} />}
          {!loading && !error && !activeRecommendation && <EmptyMessage text="Click Generate to get today's recommendation." />}
          {!loading && activeRecommendation && (
            <div className="mb-8">
              <RecommendationCard
                rec={activeRecommendation}
                onFeedback={handleFeedback}
                onClear={clearActiveRecommendation}
                feedbackPending={feedbackPending}
              />
            </div>
          )}
          <TryYourIdeaPanel />
        </>
      )}
    </div>
  );
}