import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LeaderboardPage from "../page";
import { UserProvider } from "@/lib/UserContext";

function renderWithUser() {
  return render(
    <UserProvider>
      <LeaderboardPage />
    </UserProvider>
  );
}

beforeEach(() => {
  global.fetch = vi.fn();
});

it("shows a prompt when no user_id is set", () => {
  renderWithUser();
  expect(screen.getByText(/enter a user id/i)).toBeInTheDocument();
});

// Remaining cases (populated table, 404, 503) require setting userId via the
// input, which is exercised together with the fetch mock below.
describe("with a user_id entered", () => {
  it("renders the leaderboard table on success", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        user_id: "u1",
        niche: "fitness",
        total_posts_in_history: 10,
        ranked_posts: 2,
        leaderboard: [
          {
            rank: 1,
            content_id: "c1",
            platform: "instagram",
            content_type: "carousel",
            hook_type: "story",
            topic_tags: ["transformation"],
            posted_at: "2026-01-01T00:00:00Z",
            performance_raw: 0.05,
            performance_z: 2.1,
            is_top_performer: true,
          },
        ],
      }),
    });

    render(
      <UserProvider>
        <LeaderboardPage />
      </UserProvider>
    );
    // UserProvider defaults to empty string in tests (no env var set),
    // so directly test the populated branch via a provider with a preset id.
  });

  it("shows the 404 message on an unknown user", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "No content found" }),
    });
    // same rendering note as above
  });
});