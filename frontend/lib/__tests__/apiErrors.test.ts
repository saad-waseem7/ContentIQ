import { it, expect, vi, beforeEach } from "vitest";
import { ApiError, clearApiCache, getLeaderboard, predictIdea } from "../api";

beforeEach(() => {
  clearApiCache();
  global.fetch = vi.fn();
});

const PAYLOAD = { hook_type: "story", content_type: "text", platform: "x", primary_topic_tag: "t", sample_caption: "c" };

it("uses a string detail as the error message", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: false, status: 404, statusText: "Not Found", json: async () => ({ detail: "No content found" }) });
  await expect(getLeaderboard("u1")).rejects.toMatchObject({ status: 404, message: "No content found" });
});

it("turns a FastAPI validation-error list into readable text instead of [object Object]", async () => {
  const detail = [
    { type: "value_error", loc: ["body", "sample_caption"], msg: "Value error, field must not be empty" },
    { type: "value_error", loc: ["body", "primary_topic_tag"], msg: "Value error, field must not be empty" },
  ];
  (global.fetch as any).mockResolvedValueOnce({ ok: false, status: 422, statusText: "Unprocessable", json: async () => ({ detail }) });
  const error = await predictIdea("u1", PAYLOAD).catch((e) => e);
  expect(error).toBeInstanceOf(ApiError);
  expect(error.message).toBe("Value error, field must not be empty; Value error, field must not be empty");
  expect(error.message).not.toContain("[object Object]");
});

it("falls back to the status text when the body has no usable detail", async () => {
  (global.fetch as any).mockResolvedValueOnce({ ok: false, status: 500, statusText: "Internal Server Error", json: async () => ({}) });
  await expect(getLeaderboard("u1")).rejects.toMatchObject({ status: 500, message: "Internal Server Error" });
});
