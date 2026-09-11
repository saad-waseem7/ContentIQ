import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import HistoryPage from "../page";
import { UserProvider } from "@/lib/UserContext";
import UserContextSelector from "@/components/UserContextSelector";

const TEST_USER_ID = "test-user-123";

function renderWithUser(userId = TEST_USER_ID) {
  return render(
    <UserProvider initialUserId={userId}>
      <HistoryPage />
    </UserProvider>
  );
}

beforeEach(() => {
  global.fetch = vi.fn();
});

it("shows a prompt when no user_id is set", () => {
  render(
    <UserProvider initialUserId="">
      <HistoryPage />
    </UserProvider>
  );
  expect(screen.getByText(/enter a user id/i)).toBeInTheDocument();
});

it("loads and renders recommendation history", async () => {
  (global.fetch as any).mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      user_id: TEST_USER_ID,
      count: 2,
      recommendations: [
        { id: "r2", idea_text: "Newer idea", format: "carousel", best_time: "Tuesday 7-9pm", rationale: "r", predicted_score: 0.7, status: "proposed", created_at: "2026-02-01T00:00:00Z" },
        { id: "r1", idea_text: "Older idea", format: "carousel", best_time: "Tuesday 7-9pm", rationale: "r", predicted_score: 0.4, status: "actioned", created_at: "2026-01-01T00:00:00Z" },
      ],
    }),
  });

  renderWithUser();
  await waitFor(() => expect(screen.getByText("Newer idea")).toBeInTheDocument());
  expect(screen.getByText("Older idea")).toBeInTheDocument();
  expect(screen.getByText("70%")).toBeInTheDocument();
  expect(screen.getByText("Pending")).toBeInTheDocument();
  expect(screen.getByText("Actioned")).toBeInTheDocument();
});

it("shows empty state when there is no history", async () => {
  (global.fetch as any).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ user_id: TEST_USER_ID, count: 0, recommendations: [] }),
  });
  renderWithUser();
  await waitFor(() => expect(screen.getByText(/No recommendations generated yet/i)).toBeInTheDocument());
});

it("shows an error message when the request fails", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({ detail: "not found" }) });
  renderWithUser();
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
});

it("refetches when the selected user changes", async () => {
  (global.fetch as any)
    .mockResolvedValueOnce({ ok: true, json: async () => ({ user_id: "user-a", count: 1, recommendations: [
      { id: "ra", idea_text: "User A idea", format: "carousel", best_time: null, rationale: "r", predicted_score: 0.5, status: "proposed", created_at: "2026-01-01T00:00:00Z" },
    ]}) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ user_id: "user-b", count: 1, recommendations: [
      { id: "rb", idea_text: "User B idea", format: "carousel", best_time: null, rationale: "r", predicted_score: 0.5, status: "proposed", created_at: "2026-01-01T00:00:00Z" },
    ]}) });

  render(
    <UserProvider initialUserId="user-a">
      <UserContextSelector />
      <HistoryPage />
    </UserProvider>
  );

  await waitFor(() => expect(screen.getByText("User A idea")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText(/viewing user/i), { target: { value: "user-b" } });
  await waitFor(() => expect(screen.getByText("User B idea")).toBeInTheDocument());
});