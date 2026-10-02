import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { it, expect, vi, beforeEach } from "vitest";
import { UserProvider } from "@/lib/UserContext";
import TryYourIdeaPanel from "../TryYourIdeaPanel";

beforeEach(() => {
  global.fetch = vi.fn();
});

function renderPanel() {
  return render(
    <UserProvider initialUserId="test-user-123">
      <TryYourIdeaPanel />
    </UserProvider>
  );
}

it("submits the form and displays the predicted score", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => ({ predicted_score: 0.55 }) });
  renderPanel();
  fireEvent.change(screen.getByPlaceholderText(/topic/i), { target: { value: "transformation" } });
  fireEvent.change(screen.getByPlaceholderText(/caption or title/i), { target: { value: "My own idea caption." } });
  fireEvent.click(screen.getByRole("button", { name: /score this idea/i }));
  await waitFor(() => expect(screen.getByText("55%")).toBeInTheDocument());
});

it("shows an error message when scoring fails", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({ detail: "no winning content" }) });
  renderPanel();
  fireEvent.change(screen.getByPlaceholderText(/topic/i), { target: { value: "transformation" } });
  fireEvent.change(screen.getByPlaceholderText(/caption or title/i), { target: { value: "My own idea caption." } });
  fireEvent.click(screen.getByRole("button", { name: /score this idea/i }));
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
});

function submitIdea(topic = "transformation") {
  fireEvent.change(screen.getByPlaceholderText(/topic/i), { target: { value: topic } });
  fireEvent.change(screen.getByPlaceholderText(/caption or title/i), { target: { value: "My own idea caption." } });
  fireEvent.click(screen.getByRole("button", { name: /score this idea/i }));
}

it("warns when the model has never seen the topic", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => ({ predicted_score: 0.4, topic_recognized: false }) });
  renderPanel();
  submitIdea("gardening");
  await waitFor(() => expect(screen.getByText("40%")).toBeInTheDocument());
  expect(screen.getByRole("note")).toHaveTextContent(/hasn't seen this topic/i);
});

it("shows no topic warning when the topic is recognized or the field is absent", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => ({ predicted_score: 0.4, topic_recognized: true }) });
  renderPanel();
  submitIdea();
  await waitFor(() => expect(screen.getByText("40%")).toBeInTheDocument());
  expect(screen.queryByRole("note")).not.toBeInTheDocument();
});

it("clears the previous topic warning when scoring again", async () => {
  (global.fetch as any)
    .mockResolvedValueOnce({ ok: true, json: async () => ({ predicted_score: 0.4, topic_recognized: false }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ predicted_score: 0.7, topic_recognized: true }) });
  renderPanel();
  submitIdea("gardening");
  await waitFor(() => expect(screen.getByRole("note")).toBeInTheDocument());
  submitIdea("transformation");
  await waitFor(() => expect(screen.getByText("70%")).toBeInTheDocument());
  expect(screen.queryByRole("note")).not.toBeInTheDocument();
});

