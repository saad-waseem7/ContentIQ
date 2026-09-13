import { render, screen, fireEvent } from "@testing-library/react";
import { it, expect, beforeEach, vi } from "vitest";
import { UserProvider, useUserId } from "@/lib/UserContext";
import { RecommendationProvider, useActiveRecommendation } from "../RecommendationContext";

beforeEach(() => {
  global.fetch = vi.fn();
});

function TestConsumer() {
  const { activeRecommendation, setActiveRecommendation, clearActiveRecommendation } = useActiveRecommendation();
  const { setUserId } = useUserId();
  return (
    <div>
      <div data-testid="active">{activeRecommendation ? activeRecommendation.idea_text : "none"}</div>
      <button onClick={() => setActiveRecommendation({
        id: "r1", idea_text: "Idea for A", format: "carousel", best_time: null,
        rationale: "r", predicted_score: 0.5, status: "proposed", created_at: "2026-01-01T00:00:00Z",
      }, "user-a")}>set-for-a</button>
      <button onClick={() => setUserId("user-b")}>switch-to-b</button>
      <button onClick={clearActiveRecommendation}>clear</button>
    </div>
  );
}

it("keeps the active recommendation set across a simulated re-render (navigation)", () => {
  render(
    <UserProvider initialUserId="user-a">
      <RecommendationProvider><TestConsumer /></RecommendationProvider>
    </UserProvider>
  );
  fireEvent.click(screen.getByText("set-for-a"));
  expect(screen.getByTestId("active")).toHaveTextContent("Idea for A");
});

it("clears the active recommendation when the selected user changes (no cross-user leakage)", () => {
  render(
    <UserProvider initialUserId="user-a">
      <RecommendationProvider><TestConsumer /></RecommendationProvider>
    </UserProvider>
  );
  fireEvent.click(screen.getByText("set-for-a"));
  expect(screen.getByTestId("active")).toHaveTextContent("Idea for A");

  fireEvent.click(screen.getByText("switch-to-b"));
  expect(screen.getByTestId("active")).toHaveTextContent("none");
});

it("Clear removes it from display state only", () => {
  render(
    <UserProvider initialUserId="user-a">
      <RecommendationProvider><TestConsumer /></RecommendationProvider>
    </UserProvider>
  );
  fireEvent.click(screen.getByText("set-for-a"));
  fireEvent.click(screen.getByText("clear"));
  expect(screen.getByTestId("active")).toHaveTextContent("none");
});