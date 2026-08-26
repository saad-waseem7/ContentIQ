"use client";

import { RecommendationResponse } from "@/lib/api";
import { CheckCircleIcon, XCircleIcon } from "@/components/icons";

function scoreBadge(score: number): { text: string; classes: string } {
  if (score >= 0.7) return { text: "Strong fit", classes: "bg-emerald-100 text-emerald-700" };
  if (score >= 0.4) return { text: "Worth trying", classes: "bg-amber-100 text-amber-700" };
  return { text: "Experimental", classes: "bg-slate-100 text-slate-600" };
}

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
  const badge = scoreBadge(rec.predicted_score);

  return (
    <div className="border border-slate-200 rounded-lg bg-white p-6 max-w-xl shadow-sm">
      <div className="flex justify-between items-start mb-4">
        <span className="text-xs font-semibold uppercase tracking-wide text-indigo-700 bg-indigo-50 px-2 py-1 rounded">
          {rec.format}
        </span>
        <div className="text-right">
          <div className="text-2xl font-semibold text-slate-900">{(rec.predicted_score * 100).toFixed(0)}%</div>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badge.classes}`}>{badge.text}</span>
        </div>
      </div>

      <p className="text-slate-800 leading-relaxed mb-4">{rec.idea_text}</p>

      {rec.best_time && (
        <p className="text-sm text-slate-500 mb-3">
          <span className="font-medium text-slate-600">Best time to post:</span> {rec.best_time}
        </p>
      )}

      <div className="bg-slate-50 border-l-2 border-indigo-300 rounded-r px-4 py-3 mb-5">
        <p className="text-sm text-slate-600 italic">{rec.rationale}</p>
      </div>

      {isDecided ? (
        <div
          className={`flex items-center gap-2 text-sm font-medium rounded-md px-3 py-2 ${
            rec.status === "actioned" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"
          }`}
        >
          {rec.status === "actioned" ? <CheckCircleIcon /> : <XCircleIcon />}
          {rec.status === "actioned" ? "Marked as actioned" : "Dismissed"}
        </div>
      ) : (
        <div className="flex gap-3">
          <button
            onClick={() => onFeedback("actioned")}
            disabled={feedbackPending}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-sm font-medium disabled:opacity-50 transition-colors"
          >
            Mark actioned
          </button>
          <button
            onClick={() => onFeedback("dismissed")}
            disabled={feedbackPending}
            className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-md text-sm font-medium disabled:opacity-50 transition-colors"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}