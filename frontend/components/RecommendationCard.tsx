"use client";

import { RecommendationResponse } from "@/lib/api";

export default function RecommendationCard({
  rec,
  onFeedback,
  feedbackPending,
}: {
  rec: RecommendationResponse;
  onFeedback: (status: "actioned" | "dismissed") => void;
  feedbackPending: boolean;
}) {
  const isDecided = rec.status !== "proposed";
  return (
    <div className="border border-gray-300 rounded p-4 max-w-xl">
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs uppercase tracking-wide text-gray-500">{rec.format}</span>
        <span className="text-sm font-semibold">
          Predicted score: {(rec.predicted_score * 100).toFixed(0)}%
        </span>
      </div>
      <p className="mb-2">{rec.idea_text}</p>
      {rec.best_time && <p className="text-sm text-gray-600 mb-2">Best time: {rec.best_time}</p>}
      <p className="text-sm text-gray-700 italic mb-4">{rec.rationale}</p>
      {isDecided ? (
        <p className="text-sm font-medium">Status: {rec.status}</p>
      ) : (
        <div className="flex gap-2">
          <button
            onClick={() => onFeedback("actioned")}
            disabled={feedbackPending}
            className="px-3 py-1 bg-green-600 text-white rounded text-sm disabled:opacity-50"
          >
            Mark actioned
          </button>
          <button
            onClick={() => onFeedback("dismissed")}
            disabled={feedbackPending}
            className="px-3 py-1 bg-gray-200 rounded text-sm disabled:opacity-50"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}