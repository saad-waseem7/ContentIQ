import { render, screen } from "@testing-library/react";
import InsightsPage from "../page";
import { UserProvider } from "@/lib/UserContext";

beforeEach(() => {
  global.fetch = vi.fn();
});

it("shows a prompt when no user_id is set", () => {
  render(
    <UserProvider>
      <InsightsPage />
    </UserProvider>
  );
  expect(screen.getByText(/enter a user id/i)).toBeInTheDocument();
});