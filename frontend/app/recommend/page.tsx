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

  if (!userId) return <EmptyMessage text="Enter a user ID above to generate a recommendation." />;

  return (
    <div>
      <h1 className="text-lg font-semibold mb-4">Daily recommendation</h1>
      <button
        onClick={handleGenerate}
        disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded text-sm disabled:opacity-50 mb-4"
      >
        {loading ? "Generating..." : "Generate recommendation"}
      </button>
      {loading && <LoadingMessage text="Generating recommendation..." />}
      {error && <ErrorMessage text={error} />}
      {!loading && !error && !rec && <EmptyMessage text="Click Generate to get today's recommendation." />}
      {rec && <RecommendationCard rec={rec} onFeedback={handleFeedback} feedbackPending={feedbackPending} />}
    </div>
  );
}