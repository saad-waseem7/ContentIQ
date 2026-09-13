"use client";

import { useState } from "react";
import { predictIdea, ApiError } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";
import Card from "@/components/Card";
import InfoTooltip from "@/components/InfoTooltip";
import { CONTENT_TYPE_LABELS, HOOK_TYPE_LABELS, PLATFORM_LABELS } from "@/lib/labels";
import { messageForStatus } from "@/components/StatusMessage";

function scoreBadge(score: number) {
  if (score >= 0.7) return { text: "Strong fit", classes: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" };
  if (score >= 0.4) return { text: "Worth trying", classes: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300" };
  return { text: "Experimental", classes: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300" };
}

export default function TryYourIdeaPanel() {
  const { userId } = useUserId();
  const [contentType, setContentType] = useState("carousel");
  const [hookType, setHookType] = useState("story");
  const [platform, setPlatform] = useState("instagram");
  const [topic, setTopic] = useState("");
  const [caption, setCaption] = useState("");
  const [score, setScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId || !topic.trim() || !caption.trim()) return;
    setLoading(true);
    setError(null);
    setScore(null);
    predictIdea(userId, { content_type: contentType, hook_type: hookType, platform, primary_topic_tag: topic.trim(), sample_caption: caption.trim() })
      .then((r) => setScore(r.predicted_score))
      .catch((e) => setError(e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server."))
      .finally(() => setLoading(false));
  }

  if (!userId) return null;

  return (
    <Card className="p-5 mt-8">
      <div className="flex items-center gap-1.5 mb-1">
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Try Your Own Idea</h2>
        <InfoTooltip text="Score an idea of your own using the same trained model, without generating one via AI." />
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">Enter your own content idea and see how it's predicted to perform, before you post it.</p>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid sm:grid-cols-3 gap-3">
          <select value={contentType} onChange={(e) => setContentType(e.target.value)}
            className="h-9 border border-slate-300 dark:border-slate-600 rounded-md px-2 text-sm bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200">
            {Object.entries(CONTENT_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <select value={hookType} onChange={(e) => setHookType(e.target.value)}
            className="h-9 border border-slate-300 dark:border-slate-600 rounded-md px-2 text-sm bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200">
            {Object.entries(HOOK_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}
            className="h-9 border border-slate-300 dark:border-slate-600 rounded-md px-2 text-sm bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200">
            {Object.entries(PLATFORM_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic (e.g. Transformation)"
          className="w-full h-9 border border-slate-300 dark:border-slate-600 rounded-md px-3 text-sm bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500" />
        <textarea value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="Your caption or title" rows={2}
          className="w-full border border-slate-300 dark:border-slate-600 rounded-md px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500" />
        <button type="submit" disabled={loading || !topic.trim() || !caption.trim()}
          className="h-9 px-4 bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-400 text-white rounded-md text-sm font-medium disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 transition-colors">
          {loading ? "Scoring..." : "Score this idea"}
        </button>
      </form>
      {error && <p className="text-sm text-rose-600 dark:text-rose-400 mt-3" role="alert">{error}</p>}
      {score !== null && (
        <div className="mt-4 flex items-center gap-2">
          <span className="text-xl font-semibold text-slate-900 dark:text-slate-100">{(score * 100).toFixed(0)}%</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${scoreBadge(score).classes}`}>{scoreBadge(score).text}</span>
        </div>
      )}
    </Card>
  );
}