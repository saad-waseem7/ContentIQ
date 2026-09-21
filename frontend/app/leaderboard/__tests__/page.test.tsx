import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LeaderboardPage from "../page";
import { UserProvider } from "@/lib/UserContext";
import UserContextSelector from "@/components/UserContextSelector";
import { clearApiCache } from "@/lib/api";

const TEST_USER_ID = "test-user-123";

function renderWithUser(userId = TEST_USER_ID) {
  return render(
    <UserProvider initialUserId={userId}>
      <LeaderboardPage />
    </UserProvider>
  );
}

beforeEach(() => {
  clearApiCache();
  global.fetch = vi.fn();
});

it("shows a prompt when no user_id is set", () => {
  render(
    <UserProvider initialUserId="">
      <LeaderboardPage />
    </UserProvider>
  );
  expect(screen.getByText(/enter a user id/i)).toBeInTheDocument();
});

it("renders the leaderboard table with real content when a user_id is set", async () => {
  (global.fetch as any).mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      user_id: TEST_USER_ID, niche: "fitness", total_posts_in_history: 10, ranked_posts: 2,
      leaderboard: [
        { rank: 1, content_id: "c1", platform: "instagram", content_type: "carousel", hook_type: "story",
          topic_tags: ["transformation"], posted_at: "2026-01-01T00:00:00Z", performance_raw: 0.05, performance_z: 2.1, is_top_performer: true },
        { rank: 2, content_id: "c2", platform: "tiktok", content_type: "short_video", hook_type: "question",
          topic_tags: ["mindset"], posted_at: "2026-01-02T00:00:00Z", performance_raw: 0.03, performance_z: 0.4, is_top_performer: false },
      ],
    }),
  });

  renderWithUser();

  await waitFor(() => expect(screen.getByText("Carousel")).toBeInTheDocument());
  expect(screen.getByText("Short Video")).toBeInTheDocument();
  expect(screen.getByText(/2 ranked of 10 total posts/i)).toBeInTheDocument();
});

it("shows the 404 message for an unknown user", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({ detail: "No content found" }) });
  renderWithUser();
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  expect(screen.getByText(/No data for this user ID/i)).toBeInTheDocument();
});

it("shows the empty state when the user has no ranked posts", async () => {
  (global.fetch as any).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ user_id: TEST_USER_ID, niche: "fitness", total_posts_in_history: 1, ranked_posts: 0, leaderboard: [] }),
  });
  renderWithUser();
  await waitFor(() => expect(screen.getByText(/No ranked posts yet/i)).toBeInTheDocument());
});

it("re-fetches the leaderboard when the selected user changes", async () => {
  (global.fetch as any)
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ user_id: "user-a", niche: "fitness", total_posts_in_history: 5, ranked_posts: 1,
        leaderboard: [{ rank: 1, content_id: "c1", platform: "instagram", content_type: "carousel", hook_type: "story",
          topic_tags: ["transformation"], posted_at: "2026-01-01T00:00:00Z", performance_raw: 0.05, performance_z: 2.1, is_top_performer: true }] }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ user_id: "user-b", niche: "tech", total_posts_in_history: 3, ranked_posts: 1,
        leaderboard: [{ rank: 1, content_id: "c2", platform: "youtube", content_type: "long_video", hook_type: "bold_claim",
          topic_tags: ["ai_news"], posted_at: "2026-01-02T00:00:00Z", performance_raw: 0.02, performance_z: 1.5, is_top_performer: true }] }),
    });

  render(
    <UserProvider initialUserId="user-a">
      <UserContextSelector />
      <LeaderboardPage />
    </UserProvider>
  );

  await waitFor(() => expect(screen.getByText("Carousel")).toBeInTheDocument());

  fireEvent.change(screen.getByLabelText(/viewing user/i), { target: { value: "user-b" } });

  await waitFor(() => expect(screen.getByText("Long Video")).toBeInTheDocument());
  expect((global.fetch as any).mock.calls[1][0]).toContain("user_id=user-b");
});

it("shows a leaderboard skeleton while loading, then the real table once loaded", async () => {
  let resolveFetch: (v: any) => void;
  const pending = new Promise((resolve) => { resolveFetch = resolve; });
  (global.fetch as any).mockReturnValueOnce(pending);

  renderWithUser();
  expect(screen.getByRole("status", { name: /loading leaderboard/i })).toBeInTheDocument();

  resolveFetch!({
    ok: true,
    json: async () => ({ user_id: TEST_USER_ID, niche: "fitness", total_posts_in_history: 1, ranked_posts: 1,
      leaderboard: [{ rank: 1, content_id: "c1", platform: "instagram", content_type: "carousel", hook_type: "story",
        topic_tags: ["transformation"], posted_at: "2026-01-01T00:00:00Z", performance_raw: 0.05, performance_z: 2.1, is_top_performer: true }] }),
  });

  await waitFor(() => expect(screen.getByText("Carousel")).toBeInTheDocument());
  expect(screen.queryByRole("status", { name: /loading leaderboard/i })).not.toBeInTheDocument();
});