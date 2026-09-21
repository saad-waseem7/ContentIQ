import { describe, it, expect, vi, beforeEach } from "vitest";
import { getLeaderboard, clearApiCache, invalidateCache } from "@/lib/api";

beforeEach(() => {
  clearApiCache();
  global.fetch = vi.fn();
});

it("does not re-fetch an identical URL within the cache window", async () => {
  (global.fetch as any).mockResolvedValue({
    ok: true,
    json: async () => ({ user_id: "u1", niche: "fitness", total_posts_in_history: 1, ranked_posts: 0, leaderboard: [] }),
  });

  await getLeaderboard("u1");
  await getLeaderboard("u1");

  expect((global.fetch as any).mock.calls.length).toBe(1);
});

it("fetches again for a different user_id (no cross-user leakage)", async () => {
  (global.fetch as any).mockResolvedValue({
    ok: true,
    json: async () => ({ user_id: "u2", niche: "fitness", total_posts_in_history: 1, ranked_posts: 0, leaderboard: [] }),
  });

  await getLeaderboard("u1");
  await getLeaderboard("u2");

  expect((global.fetch as any).mock.calls.length).toBe(2);
});

it("fetches again after invalidateCache is called for a matching prefix", async () => {
  (global.fetch as any).mockResolvedValue({
    ok: true,
    json: async () => ({ user_id: "u1", niche: "fitness", total_posts_in_history: 1, ranked_posts: 0, leaderboard: [] }),
  });

  await getLeaderboard("u1");
  invalidateCache("http://localhost:8000/content");
  await getLeaderboard("u1");

  expect((global.fetch as any).mock.calls.length).toBe(2);
});

it("dedupes two genuinely simultaneous requests into one network call", async () => {
  let resolveFetch: (v: any) => void;
  const pending = new Promise((resolve) => { resolveFetch = resolve; });
  (global.fetch as any).mockReturnValueOnce(pending);

  const p1 = getLeaderboard("u1");
  const p2 = getLeaderboard("u1");

  resolveFetch!({
    ok: true,
    json: async () => ({ user_id: "u1", niche: "fitness", total_posts_in_history: 1, ranked_posts: 0, leaderboard: [] }),
  });

  await Promise.all([p1, p2]);
  expect((global.fetch as any).mock.calls.length).toBe(1);
});