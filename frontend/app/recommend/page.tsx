"use client";

import { useState } from "react";
import { generateRecommendation, submitFeedback, RecommendationResponse, ApiError } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";
import { LoadingMessage, EmptyMessage, ErrorMessage, messageForStatus } from "@/components/StatusMessage";
import RecommendationCard from "@/components/RecommendationCard";

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
      <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-1">Daily recommendation</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">A grounded content idea, scored against this creator's own performance model.</p>

      {!userId && <EmptyMessage text="Enter a user ID above to generate a recommendation." />}

      {userId && (
        <>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-400 text-white rounded-md text-sm font-medium disabled:opacity-50 mb-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 transition-colors"
          >
            {loading ? "Generating..." : "Generate recommendation"}
          </button>
          {loading && <LoadingMessage text="Generating recommendation..." />}
          {!loading && error && <ErrorMessage text={error} />}
          {!loading && !error && !rec && <EmptyMessage text="Click Generate to get today's recommendation." />}
          {!loading && rec && <RecommendationCard rec={rec} onFeedback={handleFeedback} feedbackPending={feedbackPending} />}
        </>
      )}
    </div>
  );
}