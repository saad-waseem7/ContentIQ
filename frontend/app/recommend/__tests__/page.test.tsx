import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RecommendPage from "../page";
import { UserProvider } from "@/lib/UserContext";

const TEST_USER_ID = "test-user-123";
const REC_ID = "rec-abc";

function renderWithUser(userId = TEST_USER_ID) {
  return render(
    <UserProvider initialUserId={userId}>
      <RecommendPage />
    </UserProvider>
  );
}

function mockRecommendationResponse(status = "proposed") {
  return {
    ok: true,
    json: async () => ({
      id: REC_ID, idea_text: "[carousel / story hook / transformation] Test idea text.",
      format: "carousel", best_time: "Tuesday 7-9pm", rationale: "Beat your median by 2x.",
      predicted_score: 0.62, status, created_at: "2026-01-01T00:00:00Z",
    }),
  };
}

beforeEach(() => {
  global.fetch = vi.fn();
});

it("shows a prompt when no user_id is set", () => {
  render(
    <UserProvider initialUserId="">
      <RecommendPage />
    </UserProvider>
  );
  expect(screen.getByText(/enter a user id/i)).toBeInTheDocument();
});

it("generates and renders a recommendation, then marks it actioned", async () => {
  (global.fetch as any)
    .mockResolvedValueOnce(mockRecommendationResponse("proposed"))
    .mockResolvedValueOnce(mockRecommendationResponse("actioned"));

  renderWithUser();
  fireEvent.click(screen.getByRole("button", { name: /generate recommendation/i }));

  await waitFor(() => expect(screen.getByText(/Test idea text/i)).toBeInTheDocument());
  expect(screen.getByText(/62%/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /mark actioned/i }));
  await waitFor(() => expect(screen.getByText(/Marked as actioned/i)).toBeInTheDocument());

  const feedbackCall = (global.fetch as any).mock.calls[1];
  expect(feedbackCall[0]).toContain(`/recommendations/${REC_ID}/feedback`);
  expect(JSON.parse(feedbackCall[1].body)).toEqual({ status: "actioned" });
});

it("generates a recommendation and marks it dismissed", async () => {
  (global.fetch as any)
    .mockResolvedValueOnce(mockRecommendationResponse("proposed"))
    .mockResolvedValueOnce(mockRecommendationResponse("dismissed"));

  renderWithUser();
  fireEvent.click(screen.getByRole("button", { name: /generate recommendation/i }));
  await waitFor(() => expect(screen.getByText(/Test idea text/i)).toBeInTheDocument());

  fireEvent.click(screen.getByRole("button", { name: /^dismiss$/i }));
  await waitFor(() => expect(screen.getByText(/^Dismissed$/i)).toBeInTheDocument());
});

it("shows an error message when generation fails", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: false, status: 502, json: async () => ({ detail: "LLM failed" }) });
  renderWithUser();
  fireEvent.click(screen.getByRole("button", { name: /generate recommendation/i }));
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  expect(screen.getByText(/Couldn't generate a recommendation/i)).toBeInTheDocument();
});