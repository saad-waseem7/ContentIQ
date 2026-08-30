import { render, screen, fireEvent } from "@testing-library/react";
import { it, expect, beforeEach } from "vitest";
import { ThemeProvider } from "@/lib/ThemeContext";
import ThemeToggle from "../ThemeToggle";

beforeEach(() => {
  document.documentElement.classList.remove("dark");
  localStorage.clear();
});

it("toggles the dark class on <html> and persists the choice", () => {
  render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>
  );

  expect(document.documentElement.classList.contains("dark")).toBe(false);

  fireEvent.click(screen.getByRole("button"));
  expect(document.documentElement.classList.contains("dark")).toBe(true);
  expect(localStorage.getItem("contentiq-theme")).toBe("dark");

  fireEvent.click(screen.getByRole("button"));
  expect(document.documentElement.classList.contains("dark")).toBe(false);
  expect(localStorage.getItem("contentiq-theme")).toBe("light");
});