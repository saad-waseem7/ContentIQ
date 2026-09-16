"use client";

import { useEffect, useState } from "react";
import { getInsights, InsightsResponse, DimensionEntry, ApiError } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";
import { LoadingMessage, EmptyMessage, ErrorMessage, messageForStatus } from "@/components/StatusMessage";
import DimensionList from "@/components/DimensionList";
import Card from "@/components/Card";
import StatCard from "@/components/StatCard";
import InfoTooltip from "@/components/InfoTooltip";
import TrendChart from "@/components/TrendChart";
import TopicBarChart from "@/components/TopicBarChart";
import PageHeader from "@/components/PageHeader";
import { label as humanLabel, describePerformance, signed } from "@/lib/labels";

function Section({ title, subtitle, action, children }: { title: string; subtitle?: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card className="p-5 mb-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
          {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="mt-3">{children}</div>
    </Card>
  );
}

function topEntry(entries: DimensionEntry[]): DimensionEntry | null {
  return entries.length > 0 ? entries[0] : null;
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

  const helper = (
    <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5 mt-1">
      0 = typical for you. Positive means above your baseline, negative means below.
      <InfoTooltip text="Performance is measured in standard deviations (SD) from your personal baseline. It is not a percentage or a score out of 10." />
    </p>
  );

  if (!userId) {
    return (
      <div>
        <PageHeader title="Insights" subtitle="Patterns grounded in this creator's own history" helper={helper} />
        <EmptyMessage text="Enter a user ID above to see their insights." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Insights"
        subtitle={data ? `${humanLabel("niche", data.niche)} · Patterns grounded in this creator's own history` : "Patterns grounded in this creator's own history"}
        helper={helper}
      />

      {loading && <LoadingMessage text="Analyzing Performance Patterns..." />}
      {!loading && error && <ErrorMessage text={error} />}
      {!loading && !error && data && (
        <>
          {(() => {
            const topContentType = topEntry(data.personal_patterns.dimensions.content_type);
            const topTime = topEntry(data.personal_patterns.dimensions.posting_time_window);
            const topTopic = topEntry(data.personal_patterns.dimensions.topic);
            const topHook = topEntry(data.personal_patterns.dimensions.hook_type);
            const total = data.personal_patterns.total_posts_analyzed;

            return (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
                  <StatCard label="Top Content Type" value={topContentType ? humanLabel("content_type", topContentType.value) : "Not enough data"}
                    sublabel={topContentType ? `${((topContentType.n / total) * 100).toFixed(0)}% of posts` : undefined} />
                  <StatCard label="Best Time to Post" value={topTime ? humanLabel("posting_time_window", topTime.value) : "Not enough data"}
                    sublabel={topTime ? `${signed(topTime.mean_performance_z)} SD` : undefined} />
                  <StatCard label="Top Topic" value={topTopic ? humanLabel("topic", topTopic.value) : "Not enough data"}
                    sublabel={topTopic ? `${((topTopic.n / total) * 100).toFixed(0)}% of top content` : undefined} />
                  <StatCard label="Strongest Hook" value={topHook ? humanLabel("hook_type", topHook.value) : "Not enough data"}
                    sublabel={topHook ? `${signed(topHook.mean_performance_z)} SD` : undefined} />
                </div>

                <Section title="What Works For You" subtitle={`Based on ${total} of your own posts with enough history to compare`}>
                  <div className="grid sm:grid-cols-2 gap-6">
                    <DimensionList title="Content Type" dimension="content_type" entries={data.personal_patterns.dimensions.content_type} />
                    <DimensionList title="Hook Type" dimension="hook_type" entries={data.personal_patterns.dimensions.hook_type} />
                    <DimensionList title="Topic" dimension="topic" entries={data.personal_patterns.dimensions.topic} />
                    <DimensionList title="Time of Day" dimension="posting_time_window" entries={data.personal_patterns.dimensions.posting_time_window} />
                  </div>
                </Section>

                {data.personal_patterns.dimensions.topic.length > 0 && (
                  <Section title="Performance by Topic" subtitle="How your average performance compares across topics you've covered">
                    <TopicBarChart entries={data.personal_patterns.dimensions.topic} />
                  </Section>
                )}

                <Section
                  title="Performance Trend"
                  subtitle="How your content performance has changed over time"
                  action={data.trend.sufficient_data && (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      data.trend.direction === "improving" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" :
                      data.trend.direction === "declining" ? "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300" :
                      "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"}`}>
                      {data.trend.direction === "improving" ? "Trending Up" : data.trend.direction === "declining" ? "Trending down" : "Stable"}
                    </span>
                  )}
                >
                  {data.trend.sufficient_data ? (
                    <div>
                      <p className="text-sm font-medium text-slate-800 dark:text-slate-200 mb-2">
                        Your recent performance is{" "}
                        {(data.trend.recent_mean_performance_z ?? 0) >= (data.trend.historical_mean_performance_z ?? 0) ? "above" : "below"}{" "}
                        your usual baseline.
                      </p>
                      <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500 dark:text-slate-400 mb-1">
                        <span>Last {data.trend.recent_period_days} days: {signed(data.trend.recent_mean_performance_z ?? 0)} SD vs. baseline</span>
                        <span>Previous period: {signed(data.trend.historical_mean_performance_z ?? 0)} SD vs. baseline</span>
                      </div>
                      <p className="text-xs text-slate-400 dark:text-slate-500 italic">{data.trend.note}</p>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 dark:text-slate-500">Not enough posts yet on both sides of a recent/historical split to show a trend.</p>
                  )}
                  {data.monthly_performance.length > 0 && <div className="mt-4"><TrendChart data={data.monthly_performance} /></div>}
                </Section>

                <Section title="You vs. Your Niche" subtitle="Population-level evidence, kept separate from your personal patterns above">
                  {data.niche_comparison.sufficient_data ? (
                    <p className="text-sm text-slate-700 dark:text-slate-300 flex items-center gap-1.5 flex-wrap">
                      You're averaging{" "}
                      <span className="font-medium">{(data.niche_comparison.delta ?? 0) > 0 ? "above" : "below"} the typical creator</span>{" "}
                      in {humanLabel("niche", data.niche)}, based on {data.niche_comparison.niche_other_users_n} other creators and {data.niche_comparison.niche_total_posts_n} posts.
                      <InfoTooltip text={`Your average: ${signed(data.niche_comparison.user_mean_performance_z ?? 0)} SD. Niche average: ${signed(data.niche_comparison.niche_mean_performance_z ?? 0)} SD.`} />
                    </p>
                  ) : (
                    <p className="text-xs text-slate-400 dark:text-slate-500">Not enough other creators in this niche yet to compare against.</p>
                  )}
                </Section>

                {data.niche_top_patterns.length > 0 && (
                  <Section title="Patterns Across This Niche" subtitle="Not personal to you — broader population evidence">
                    <ul className="space-y-3">
                      {data.niche_top_patterns.map((p, i) => {
                        const perf = describePerformance(p.mean_performance_z, p.n);
                        const color = perf.direction === "above" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400";
                        return (
                          <li key={i} className="border-b border-slate-100 dark:border-slate-700/60 last:border-0 pb-3 last:pb-0">
                            <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{humanLabel(p.dimension, p.value)}</p>
                            <p className={`text-xs ${color}`}>{perf.sdLine}</p>
                            <p className="text-xs text-slate-400 dark:text-slate-500">{perf.postsLine}</p>
                          </li>
                        );
                      })}
                    </ul>
                  </Section>
                )}

                <Section title="Topic Clusters" subtitle="Grouped by caption similarity across this niche">
                  {data.topic_clusters.available ? (
                    <ul className="space-y-3">
                      {data.topic_clusters.clusters?.map((c) => {
                        const perf = describePerformance(c.mean_performance_z, c.n);
                        const color = perf.direction === "above" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400";
                        return (
                          <li key={c.cluster_id} className="border border-slate-100 dark:border-slate-700 rounded p-3">
                            <div className="flex justify-between items-center mb-1">
                              <span className="text-sm text-slate-700 dark:text-slate-300">
                                {humanLabel("content_type", c.dominant_content_type)} · {humanLabel("hook_type", c.dominant_hook_type)} · {humanLabel("topic", c.dominant_topic_tag)}
                              </span>
                              {c.is_high_performing && (
                                <span className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 px-1.5 py-0.5 rounded-full">High Performing</span>
                              )}
                            </div>
                            <p className={`text-xs ${color}`}>{perf.sdLine}</p>
                            <p className="text-xs text-slate-400 dark:text-slate-500">{perf.postsLine} in niche</p>
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-400 dark:text-slate-500">{data.topic_clusters.reason_unavailable}</p>
                  )}
                </Section>
              </>
            );
          })()}
        </>
      )}
    </div>
  );
}