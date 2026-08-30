import { render, screen, fireEvent } from "@testing-library/react";
import { it, expect, vi, beforeEach } from "vitest";
import { UserProvider, useUserId } from "@/lib/UserContext";
import UserContextSelector from "../UserContextSelector";

function Consumer() {
  const { userId } = useUserId();
  return <div data-testid="current-user">{userId || "none"}</div>;
}

beforeEach(() => {
  global.fetch = vi.fn();
});

it("updates the shared user context when the input changes", () => {
  render(
    <UserProvider initialUserId="">
      <UserContextSelector />
      <Consumer />
    </UserProvider>
  );

  expect(screen.getByTestId("current-user")).toHaveTextContent("none");
  fireEvent.change(screen.getByLabelText(/viewing user/i), { target: { value: "new-user-id" } });
  expect(screen.getByTestId("current-user")).toHaveTextContent("new-user-id");
});