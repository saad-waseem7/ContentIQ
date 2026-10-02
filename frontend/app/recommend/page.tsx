"use client";

import { useEffect, useRef, useState } from "react";
import { generateRecommendation, submitFeedback, ApiError } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";
import { useActiveRecommendation } from "@/lib/RecommendationContext";
import { ErrorMessage, EmptyMessage, messageForStatus } from "@/components/StatusMessage";
import PageHeader from "@/components/PageHeader";
import RecommendationCard from "@/components/RecommendationCard";
import RecommendationCardSkeleton from "@/components/skeletons/RecommendationCardSkeleton";
import TryYourIdeaPanel from "@/components/TryYourIdeaPanel";

export default function RecommendPage() {
  const { userId } = useUserId();
  const { activeRecommendation, setActiveRecommendation, updateActiveRecommendationStatus, clearActiveRecommendation } = useActiveRecommendation();
  const [loading, setLoading] = useState(false);
  const [feedbackPending, setFeedbackPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selecting a different user resets this page's transient state, and requests that were
  // started for the previous user must not touch it when they finish.
  const selectedUserRef = useRef(userId);
  useEffect(() => {
    selectedUserRef.current = userId;
    setLoading(false);
    setFeedbackPending(false);
    setError(null);
  }, [userId]);

  function handleGenerate() {
    if (!userId) return;
    const requestedFor = userId;
    const stillSelected = () => selectedUserRef.current === requestedFor;
    setLoading(true);
    setError(null);
    generateRecommendation(requestedFor)
      .then((rec) => {
        if (stillSelected()) setActiveRecommendation(rec, requestedFor);
      })
      .catch((e) => {
        if (stillSelected()) setError(e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server.");
      })
      .finally(() => {
        if (stillSelected()) setLoading(false);
      });
  }

  function handleFeedback(status: "actioned" | "dismissed") {
    if (!activeRecommendation) return;
    const requestedFor = userId;
    const stillSelected = () => selectedUserRef.current === requestedFor;
    setFeedbackPending(true);
    setError(null);
    submitFeedback(activeRecommendation.id, status)
      .then((rec) => {
        if (stillSelected()) updateActiveRecommendationStatus(rec);
      })
      .catch((e) => {
        if (stillSelected()) setError(e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server.");
      })
      .finally(() => {
        if (stillSelected()) setFeedbackPending(false);
      });
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

          {loading && (
            <div className="mb-8">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">Generating Recommendation…</p>
              <RecommendationCardSkeleton />
            </div>
          )}
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
          <TryYourIdeaPanel key={userId} />
        </>
      )}
    </div>
  );
}