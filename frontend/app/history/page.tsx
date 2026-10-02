"use client";

import { useEffect, useState } from "react";
import { getRecommendationHistory, RecommendationHistoryResponse, ApiError } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";
import { EmptyMessage, ErrorMessage, messageForStatus } from "@/components/StatusMessage";
import HistoryListSkeleton from "@/components/skeletons/HistoryListSkeleton";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import { formatDate, formatIdeaText } from "@/lib/labels";

function statusBadge(status: string) {
  if (status === "actioned") return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300";
  if (status === "dismissed") return "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300";
  return "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300";
}

function statusText(status: string) {
  if (status === "proposed") return "Pending";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function HistoryPage() {
  const { userId } = useUserId();
  const [data, setData] = useState<RecommendationHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    // Ignore responses that arrive after the selected user changed.
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    getRecommendationHistory(userId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (cancelled) return;
        const msg = e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server.";
        setError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  return (
    <div>
      <PageHeader title="Recommendation History" subtitle="Previously generated recommendations for this creator." />

      {!userId && <EmptyMessage text="Enter a user ID above to see their recommendation history." />}
      {userId && loading && <HistoryListSkeleton />}
      {userId && !loading && error && <ErrorMessage text={error} />}
      {userId && !loading && !error && data && data.count === 0 && (
        <EmptyMessage text="No recommendations generated yet for this user." />
      )}
      {userId && !loading && !error && data && data.count > 0 && (
        <Card className="overflow-hidden">
          <ul>
            {data.recommendations.map((rec) => (
              <li key={rec.id} className="border-b border-slate-100 dark:border-slate-700/60 last:border-0 px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-xs text-slate-400 dark:text-slate-500 mb-1">{formatDate(rec.created_at)}</p>
                    <p className="text-sm text-slate-800 dark:text-slate-200">{formatIdeaText(rec.idea_text)}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {(rec.predicted_score * 100).toFixed(0)}%
                    </span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusBadge(rec.status)}`}>
                      {statusText(rec.status)}
                    </span>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}