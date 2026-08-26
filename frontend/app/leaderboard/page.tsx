"use client";

import { useEffect, useState } from "react";
import { getLeaderboard, LeaderboardResponse, ApiError } from "@/lib/api";
import { useUserId } from "@/lib/UserContext";
import { LoadingMessage, EmptyMessage, ErrorMessage, messageForStatus } from "@/components/StatusMessage";
import LeaderboardTable from "@/components/LeaderboardTable";

export default function LeaderboardPage() {
  const { userId } = useUserId();
  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    setData(null);
    getLeaderboard(userId)
      .then(setData)
      .catch((e) => {
        const msg = e instanceof ApiError ? messageForStatus(e.status, e.message) : "Couldn't reach the server.";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [userId]);

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900 mb-1">Content performance leaderboard</h1>
      <p className="text-sm text-slate-500 mb-6">Ranked by performance relative to this creator's own baseline.</p>

      {!userId && <EmptyMessage text="Enter a user ID above to see their leaderboard." />}
      {userId && loading && <LoadingMessage text="Loading leaderboard..." />}
      {userId && !loading && error && <ErrorMessage text={error} />}
      {userId && !loading && !error && data && data.ranked_posts === 0 && (
        <EmptyMessage text="No ranked posts yet for this user." />
      )}
      {userId && !loading && !error && data && data.ranked_posts > 0 && (
        <>
          <p className="text-sm text-slate-500 mb-3">
            {data.ranked_posts} ranked of {data.total_posts_in_history} total posts · {data.niche}
          </p>
          <LeaderboardTable entries={data.leaderboard} />
        </>
      )}
    </div>
  );
}