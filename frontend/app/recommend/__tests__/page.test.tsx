import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RecommendPage from "../page";
import { UserProvider } from "@/lib/UserContext";

beforeEach(() => {
  global.fetch = vi.fn();
});

it("shows a prompt when no user_id is set", () => {
  render(
    <UserProvider>
      <RecommendPage />
    </UserProvider>
  );
  expect(screen.getByText(/enter a user id/i)).toBeInTheDocument();
});