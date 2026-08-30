"use client";

import { useState } from "react";
import { generateRecommendation, submitFeedback, RecommendationResponse, ApiError } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";
import { LoadingMessage, EmptyMessage, ErrorMessage, messageForStatus } from "@/components/StatusMessage";
import RecommendationCard from "@/components/RecommendationCard";
import PageHeader from "@/components/PageHeader";
import TryYourIdeaPanel from "@/components/TryYourIdeaPanel";

export default function RecommendPage() {
  const { userId } = useUserId();
  const [rec, setRec] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedbackPending, setFeedbackPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleGenerate() {
    if (!userId) return;
    setLoading(true);
    setError(null);
    generateRecommendation(userId)
      .then(setRec)
      .catch((e) => {
        const msg = e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server.";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }

  function handleFeedback(status: "actioned" | "dismissed") {
    if (!rec) return;
    setFeedbackPending(true);
    submitFeedback(rec.id, status)
      .then(setRec)
      .catch((e) => {
        const msg = e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server.";
        setError(msg);
      })
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
          {loading && <LoadingMessage text="Generating recommendation..." />}
          {!loading && error && <ErrorMessage text={error} />}
          {!loading && !error && !rec && <EmptyMessage text="Click Generate to get today's recommendation." />}
          {!loading && rec && <RecommendationCard rec={rec} onFeedback={handleFeedback} feedbackPending={feedbackPending} />}
          <TryYourIdeaPanel />
        </>
      )}
    </div>
  );
}