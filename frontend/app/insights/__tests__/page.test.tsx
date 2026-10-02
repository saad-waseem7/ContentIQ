import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InsightsPage from "../page";
import { UserProvider } from "@/lib/UserContext";
import { ThemeProvider } from "@/lib/ThemeContext";
import { clearApiCache } from "@/lib/api";

const TEST_USER_ID = "test-user-123";

function renderWithUser(userId = TEST_USER_ID) {
  return render(
    <ThemeProvider>
      <UserProvider initialUserId={userId}>
        <InsightsPage />
      </UserProvider>
    </ThemeProvider>
  );
}

function mockInsightsResponse() {
  return {
    ok: true,
    json: async () => ({
      user_id: TEST_USER_ID, niche: "fitness",
      personal_patterns: {
        total_posts_analyzed: 150,
        dimensions: {
          hook_type: [{ value: "story", n: 30, mean_performance_z: 1.1, is_standout: true }],
          topic: [{ value: "transformation", n: 37, mean_performance_z: 0.94, is_standout: true }],
          posting_time_window: [{ value: "evening", n: 32, mean_performance_z: 1.01, is_standout: true }],
        },
      },
      trend: { sufficient_data: true, recent_period_days: 60, recent_mean_performance_z: -0.21, recent_n: 22,
        historical_mean_performance_z: 0.2, historical_n: 100, direction: "declining", note: "Descriptive only — reflects what happened, not why." },
      monthly_performance: [{ period: "2026-01", mean_performance_z: 0.3, n: 10 }],
      niche_comparison: { sufficient_data: true, user_n: 150, niche_other_users_n: 24, niche_total_posts_n: 4000,
        user_median_engagement_rate: 0.1, niche_median_engagement_rate: 0.05, engagement_ratio: 2.0 },
      niche_top_patterns: [{ dimension: "topic", value: "transformation", n: 800, mean_performance_z: 0.9, is_standout: true }],
      topic_clusters: { available: true, reason_unavailable: null, k: 4, silhouette_score: 0.5,
        clusters: [{ cluster_id: 0, n: 200, mean_performance_z: 0.8, dominant_content_type: "carousel", dominant_hook_type: "story", dominant_topic_tag: "transformation", is_high_performing: true }],
        user_cluster_summary: [{ cluster_id: 0, user_post_count: 50 }] },
    }),
  };
}

beforeEach(() => {
  clearApiCache();
  global.fetch = vi.fn();
});

it("shows a prompt when no user_id is set", () => {
  render(
    <ThemeProvider>
      <UserProvider initialUserId="">
        <InsightsPage />
      </UserProvider>
    </ThemeProvider>
  );
  expect(screen.getByText(/enter a user id/i)).toBeInTheDocument();
});

it("renders personal patterns, trend, niche comparison and clusters for a real user", async () => {
  (global.fetch as any).mockResolvedValueOnce(mockInsightsResponse());
  renderWithUser();

  await waitFor(() => expect(screen.getByText(/What Works For You/i)).toBeInTheDocument());
  expect(screen.getAllByText(/Transformation/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Based on 150 of your own posts/i)).toBeInTheDocument();
  expect(screen.getByText(/Performance trend/i)).toBeInTheDocument();
  expect(screen.getByText(/You vs\. your niche/i)).toBeInTheDocument();
  expect(screen.getByText(/Topic clusters/i)).toBeInTheDocument();
  expect(screen.queryByText(/n=\d/)).not.toBeInTheDocument();
});

it("shows an error message when the request fails", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: "not built" }) });
  renderWithUser();
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
});

it("shows an insights skeleton while loading, then real content once loaded", async () => {
  let resolveFetch: (v: any) => void;
  const pending = new Promise((resolve) => { resolveFetch = resolve; });
  (global.fetch as any).mockReturnValueOnce(pending);

  renderWithUser();
  expect(screen.getByRole("status", { name: /loading insights/i })).toBeInTheDocument();

  resolveFetch!(mockInsightsResponse());
  await waitFor(() => expect(screen.getByText("What Works For You")).toBeInTheDocument());
  expect(screen.queryByRole("status", { name: /loading insights/i })).not.toBeInTheDocument();
});

it("compares absolute engagement against similar posts, not z-scores", async () => {
  (global.fetch as any).mockResolvedValueOnce(mockInsightsResponse());
  renderWithUser();
  await waitFor(() => expect(screen.getByText(/You vs\. your niche/i)).toBeInTheDocument());
  expect(screen.getByText(/10\.0% engagement/)).toBeInTheDocument();
  expect(screen.getByText("higher than")).toBeInTheDocument();
  expect(screen.getByText(/5\.0% typical/)).toBeInTheDocument();
  expect(screen.getByText(/\(2\.0x\)/)).toBeInTheDocument();
});

it("says 'about the same as' instead of forcing above or below when engagement is close", async () => {
  const base = await mockInsightsResponse().json();
  base.niche_comparison = { ...base.niche_comparison, engagement_ratio: 1.03, user_median_engagement_rate: 0.0515 };
  (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => base });
  renderWithUser();
  await waitFor(() => expect(screen.getByText("about the same as")).toBeInTheDocument());
  expect(screen.queryByText(/\(1\.0x\)/)).not.toBeInTheDocument();
});

it("does not show a content-type ranking, which per-format normalization makes meaningless", async () => {
  (global.fetch as any).mockResolvedValueOnce(mockInsightsResponse());
  renderWithUser();
  await waitFor(() => expect(screen.getByText(/What Works For You/i)).toBeInTheDocument());
  expect(screen.queryByText("Top Content Type")).not.toBeInTheDocument();
  expect(screen.queryByText("Content Type")).not.toBeInTheDocument();
});

it("describes a stable trend as in line with the baseline", async () => {
  const base = await mockInsightsResponse().json();
  base.trend = { ...base.trend, direction: "stable", recent_mean_performance_z: 0.1, historical_mean_performance_z: 0.05 };
  (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => base });
  renderWithUser();
  await waitFor(() => expect(screen.getByText(/in line with/)).toBeInTheDocument());
});

