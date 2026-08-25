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

  if (!userId) return <EmptyMessage text="Enter a user ID above to see their leaderboard." />;
  if (loading) return <LoadingMessage text="Loading leaderboard..." />;
  if (error) return <ErrorMessage text={error} />;
  if (!data) return null;
  if (data.ranked_posts === 0) return <EmptyMessage text="No ranked posts yet for this user." />;

  return (
    <div>
      <h1 className="text-lg font-semibold mb-1">{data.niche} leaderboard</h1>
      <p className="text-sm text-gray-500 mb-4">
        {data.ranked_posts} ranked of {data.total_posts_in_history} total posts
      </p>
      <LeaderboardTable entries={data.leaderboard} />
    </div>
  );
}