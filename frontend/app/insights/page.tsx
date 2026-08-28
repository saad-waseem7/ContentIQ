"use client";

import { useEffect, useState } from "react";
import { getInsights, InsightsResponse, ApiError } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";
import { LoadingMessage, EmptyMessage, ErrorMessage, messageForStatus } from "@/components/StatusMessage";
import DimensionList from "@/components/DimensionList";

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="border border-slate-200 rounded-lg bg-white p-5 mb-5">
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      {subtitle && <p className="text-xs text-slate-500 mb-3">{subtitle}</p>}
      <div className="mt-3">{children}</div>
    </div>
  );
}

export default function InsightsPage() {
  const { userId } = useUserId();
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    setData(null);
    getInsights(userId)
      .then(setData)
      .catch((e) => {
        const msg = e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server.";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [userId]);

  if (!userId) return <EmptyMessage text="Enter a user ID above to see their insights." />;
  if (loading) return <LoadingMessage text="Analyzing performance patterns..." />;
  if (error) return <ErrorMessage text={error} />;
  if (!data) return null;

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900 mb-1">Insights</h1>
      <p className="text-sm text-slate-500 mb-6">{data.niche} · patterns grounded in this creator's own history</p>

      <Section title="What works for you" subtitle={`Based on ${data.personal_patterns.total_posts_analyzed} of your own posts with enough history to compare`}>
        <div className="grid sm:grid-cols-2 gap-6">
          <DimensionList title="Content type" entries={data.personal_patterns.dimensions.content_type} />
          <DimensionList title="Hook type" entries={data.personal_patterns.dimensions.hook_type} />
          <DimensionList title="Topic" entries={data.personal_patterns.dimensions.topic} />
          <DimensionList title="Time of day" entries={data.personal_patterns.dimensions.posting_time_window} />
        </div>
      </Section>

      <Section title="Trend">
        {data.trend.sufficient_data ? (
          <div>
            <span
              className={`text-sm font-medium px-2 py-0.5 rounded-full ${
                data.trend.direction === "improving" ? "bg-emerald-100 text-emerald-700" :
                data.trend.direction === "declining" ? "bg-rose-100 text-rose-700" :
                "bg-slate-100 text-slate-600"
              }`}
            >
              {data.trend.direction}
            </span>
            <p className="text-xs text-slate-500 mt-2">
              Last {data.trend.recent_period_days} days: {data.trend.recent_mean_performance_z?.toFixed(2)} (n={data.trend.recent_n}) vs.
              earlier: {data.trend.historical_mean_performance_z?.toFixed(2)} (n={data.trend.historical_n})
            </p>
            <p className="text-xs text-slate-400 italic mt-1">{data.trend.note}</p>
          </div>
        ) : (
          <p className="text-xs text-slate-400">Not enough posts yet on both sides of a recent/historical split to show a trend.</p>
        )}
      </Section>

      {data.monthly_performance.length > 0 && (
        <Section title="Performance by month">
          <ul className="space-y-1">
            {data.monthly_performance.map((m) => (
              <li key={m.period} className="flex justify-between text-sm text-slate-700">
                <span>{m.period}</span>
                <span className="text-slate-400 text-xs">{m.mean_performance_z.toFixed(2)} · n={m.n}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="You vs. your niche" subtitle="Population-level evidence, kept separate from your personal patterns above">
        {data.niche_comparison.sufficient_data ? (
          <p className="text-sm text-slate-700">
            You average <span className="font-medium">{data.niche_comparison.user_mean_performance_z?.toFixed(2)}</span>,
            vs. <span className="font-medium">{data.niche_comparison.niche_mean_performance_z?.toFixed(2)}</span> across{" "}
            {data.niche_comparison.niche_other_users_n} other creators in {data.niche} ({data.niche_comparison.niche_total_posts_n} posts).
          </p>
        ) : (
          <p className="text-xs text-slate-400">Not enough other creators in this niche yet to compare against.</p>
        )}
      </Section>

      {data.niche_top_patterns.length > 0 && (
        <Section title="Patterns across this niche" subtitle="Not personal to you — broader population evidence">
          <ul className="space-y-1.5">
            {data.niche_top_patterns.map((p, i) => (
              <li key={i} className="flex justify-between text-sm">
                <span className="text-slate-700">{p.dimension}: {p.value}</span>
                <span className="text-slate-400 text-xs">{p.mean_performance_z.toFixed(2)} · n={p.n}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Topic clusters" subtitle="Grouped by caption similarity across this niche">
        {data.topic_clusters.available ? (
          <div>
            <ul className="space-y-2">
              {data.topic_clusters.clusters?.map((c) => (
                <li key={c.cluster_id} className="border border-slate-100 rounded p-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-700">{c.dominant_content_type} / {c.dominant_hook_type} / {c.dominant_topic_tag}</span>
                    {c.is_high_performing && (
                      <span className="text-xs bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">high performing</span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400">{c.mean_performance_z.toFixed(2)} avg · n={c.n} in niche</p>
                </li>
              ))}
            </ul>
            {data.topic_clusters.user_cluster_summary.length > 0 && (
              <p className="text-xs text-slate-500 mt-3">
                Your posts fall mostly into cluster{" "}
                {data.topic_clusters.user_cluster_summary.sort((a, b) => b.user_post_count - a.user_post_count)[0].cluster_id}.
              </p>
            )}
          </div>
        ) : (
          <p className="text-xs text-slate-400">{data.topic_clusters.reason_unavailable}</p>
        )}
      </Section>
    </div>
  );
}