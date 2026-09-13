import { describe, it, expect } from "vitest";
import { label, formatIdeaText, humanizeTopic } from "../labels";

describe("label / humanizeTopic mappings", () => {
  it("formats known content types, hook types, and topics", () => {
    expect(label("content_type", "carousel")).toBe("Carousel");
    expect(label("content_type", "short_video")).toBe("Short Video");
    expect(label("hook_type", "story")).toBe("Story");
    expect(label("hook_type", "bold_claim")).toBe("Bold Claim");
    expect(humanizeTopic("debt_payoff")).toBe("Debt Payoff");
    expect(humanizeTopic("workout_routine")).toBe("Workout Routine");
    expect(humanizeTopic("nutrition_tips")).toBe("Nutrition Tips");
    expect(humanizeTopic("quick_recipes")).toBe("Quick Recipes");
  });

  it("falls back to title-case humanization for an unknown value", () => {
    expect(label("content_type", "some_future_format")).toBe("Some Future Format");
    expect(label("hook_type", "brand_new_hook")).toBe("Brand New Hook");
  });

  it("does not alter an already human-readable single word", () => {
    expect(humanizeTopic("Story")).toBe("Story");
  });
});

describe("formatIdeaText", () => {
  it("reformats a well-formed bracketed idea_text into human-readable labels", () => {
    const raw = "[carousel / story hook / debt_payoff] Three years ago, I was $45,000 in debt.";
    expect(formatIdeaText(raw)).toBe(
      "[Carousel / Story Hook / Debt Payoff] Three years ago, I was $45,000 in debt."
    );
  });

  it("reformats different content/hook/topic combinations correctly", () => {
    const raw = "[short_video / bold_claim hook / workout_routine] Most people fail their transformation.";
    expect(formatIdeaText(raw)).toBe(
      "[Short Video / Bold Claim Hook / Workout Routine] Most people fail their transformation."
    );
  });

  it("handles a topic containing multiple underscore-separated words", () => {
    const raw = "[short_video / story hook / nutrition_tips] Some caption here.";
    expect(formatIdeaText(raw)).toBe("[Short Video / Story Hook / Nutrition Tips] Some caption here.");
  });

  it("falls back to the original string unchanged if it does not match the expected format", () => {
    const raw = "Just a plain caption with no bracket metadata.";
    expect(formatIdeaText(raw)).toBe(raw);
  });

  it("does not crash or produce 'undefined' on an unrecognized enum value inside the brackets", () => {
    const raw = "[some_new_format / totally_new_hook hook / brand_new_topic] Caption text.";
    const result = formatIdeaText(raw);
    expect(result).not.toContain("undefined");
    expect(result).toBe("[Some New Format / Totally New Hook Hook / Brand New Topic] Caption text.");
  });
});