import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LeaderboardPage from "@/app/leaderboard/page";
import HistoryPage from "@/app/history/page";
import InsightsPage from "@/app/insights/page";
import RecommendPage from "@/app/recommend/page";
import { UserProvider } from "@/lib/UserContext";
import { ThemeProvider } from "@/lib/ThemeContext";
import { RecommendationProvider } from "@/lib/RecommendationContext";
import { clearApiCache } from "@/lib/api";

beforeEach(() => {
  clearApiCache();
  global.fetch = vi.fn();
});

function ok(body: unknown) {
  return { ok: true, json: async () => body };
}

function switchUserTo(id: string) {
  fireEvent.change(screen.getByLabelText(/viewing user/i), { target: { value: id } });
}

function renderApp(page: React.ReactNode, initial = "user-A") {
  return render(
    <ThemeProvider>
      <UserProvider initialUserId={initial}>
        <RecommendationProvider>{page}</RecommendationProvider>
      </UserProvider>
    </ThemeProvider>
  );
}

// A request for user-A that is slow, and one for user-B that is fast. Route by the user_id in the URL.
function routeByUser(slowA: Promise<unknown>, bodyForB: unknown) {
  (global.fetch as any).mockImplementation((url: string) =>
    url.includes("user_id=user-A") ? slowA : Promise.resolve(ok(bodyForB))
  );
}

const board = (niche: string) => ({
  user_id: "x", niche, total_posts_in_history: 5, ranked_posts: 1,
  leaderboard: [{ rank: 1, content_id: "c1", platform: "instagram", content_type: "carousel", hook_type: "story",
    topic_tags: [niche], posted_at: "2026-01-01T00:00:00Z", performance_raw: 0.05, performance_z: 2.1, is_top_performer: true }],
});

const history = (text: string) => ({
  user_id: "x", count: 1,
  recommendations: [{ id: text, idea_text: text, format: "carousel", best_time: null, rationale: "r", predicted_score: 0.5, status: "proposed", created_at: "2026-01-01T00:00:00Z" }],
});

const insights = (niche: string) => ({
  user_id: "x", niche,
  personal_patterns: { total_posts_analyzed: 0, dimensions: { content_type: [], hook_type: [], topic: [], posting_time_window: [] } },
  trend: { sufficient_data: false, direction: "insufficient_data", note: "n" },
  monthly_performance: [],
  niche_comparison: { sufficient_data: false, user_n: 0, niche_other_users_n: 0, niche_total_posts_n: 0 },
  niche_top_patterns: [],
  topic_clusters: { available: false, reason_unavailable: "not enough data", clusters: [], user_cluster_summary: [] },
});

describe("a response that arrives after the selected user changed is ignored", () => {
  it("leaderboard", async () => {
    let resolveA!: (v: unknown) => void;
    routeByUser(new Promise((r) => (resolveA = r)), board("food"));
    renderApp(<LeaderboardPage />);

    switchUserTo("user-B");
    await waitFor(() => expect(screen.getAllByText(/Food/).length).toBeGreaterThan(0));
    await act(async () => resolveA(ok(board("fitness"))));

    expect(screen.queryAllByText(/Fitness/)).toHaveLength(0);
    expect(screen.getAllByText(/Food/).length).toBeGreaterThan(0);
  });

  it("history", async () => {
    let resolveA!: (v: unknown) => void;
    routeByUser(new Promise((r) => (resolveA = r)), history("Beta idea text"));
    renderApp(<HistoryPage />);

    switchUserTo("user-B");
    await waitFor(() => expect(screen.getByText("Beta idea text")).toBeInTheDocument());
    await act(async () => resolveA(ok(history("Alpha idea text"))));

    expect(screen.queryByText("Alpha idea text")).not.toBeInTheDocument();
    expect(screen.getByText("Beta idea text")).toBeInTheDocument();
  });

  it("insights", async () => {
    let resolveA!: (v: unknown) => void;
    routeByUser(new Promise((r) => (resolveA = r)), insights("food"));
    renderApp(<InsightsPage />);

    switchUserTo("user-B");
    await waitFor(() => expect(screen.getByText(/Food ·/)).toBeInTheDocument());
    await act(async () => resolveA(ok(insights("fitness"))));

    expect(screen.queryByText(/Fitness ·/)).not.toBeInTheDocument();
  });

  it("does not leave the skeleton stuck when the user switches mid-load", async () => {
    routeByUser(new Promise(() => {}), board("food")); // user-A never answers
    renderApp(<LeaderboardPage />);
    switchUserTo("user-B");
    await waitFor(() => expect(screen.getAllByText(/Food/).length).toBeGreaterThan(0));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("recommend page state belongs to the selected user", () => {
  it("an error for one user is not shown after switching to another", async () => {
    (global.fetch as any).mockResolvedValue({ ok: false, status: 404, json: async () => ({ detail: "x" }) });
    renderApp(<RecommendPage />);
    fireEvent.click(screen.getByRole("button", { name: /generate recommendation/i }));
    await waitFor(() => expect(screen.getByText(/No data for this user ID/i)).toBeInTheDocument());

    switchUserTo("user-B");
    expect(screen.queryByText(/No data for this user ID/i)).not.toBeInTheDocument();
  });

  it("a recommendation that finishes generating after the user switched is not shown, and Generate is not stuck", async () => {
    let resolveGenerate!: (v: unknown) => void;
    (global.fetch as any).mockImplementation(() => new Promise((r) => (resolveGenerate = r)));
    renderApp(<RecommendPage />);
    fireEvent.click(screen.getByRole("button", { name: /generate recommendation/i }));
    expect(screen.getByRole("button", { name: /generating/i })).toBeDisabled();

    switchUserTo("user-B");
    expect(screen.getByRole("button", { name: /generate recommendation/i })).toBeEnabled();

    await act(async () => resolveGenerate(ok({
      id: "r-A", idea_text: "Idea made for A", format: "carousel", best_time: null, rationale: "r",
      predicted_score: 0.5, status: "proposed", created_at: "2026-01-01T00:00:00Z",
    })));
    expect(screen.queryByText(/Idea made for A/)).not.toBeInTheDocument();
  });

  it("the Try Your Own Idea score does not carry over to another user", async () => {
    (global.fetch as any).mockResolvedValue(ok({ predicted_score: 0.78, topic_recognized: true }));
    renderApp(<RecommendPage />);
    fireEvent.change(screen.getByPlaceholderText(/topic/i), { target: { value: "transformation" } });
    fireEvent.change(screen.getByPlaceholderText(/caption or title/i), { target: { value: "idea" } });
    fireEvent.click(screen.getByRole("button", { name: /score this idea/i }));
    await waitFor(() => expect(screen.getByText("78%")).toBeInTheDocument());

    switchUserTo("user-B");
    expect(screen.queryByText("78%")).not.toBeInTheDocument();
    expect((screen.getByPlaceholderText(/topic/i) as HTMLInputElement).value).toBe("");
  });
});
