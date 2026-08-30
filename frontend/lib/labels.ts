export const CONTENT_TYPE_LABELS: Record<string, string> = {
  short_video: "Short Video", long_video: "Long Video", image: "Image",
  carousel: "Carousel", text: "Text Post",
};

export const PLATFORM_LABELS: Record<string, string> = {
  youtube: "YouTube", youtube_shorts: "YouTube Shorts", instagram: "Instagram",
  tiktok: "TikTok", x: "X (Twitter)", linkedin: "LinkedIn",
};

export const HOOK_TYPE_LABELS: Record<string, string> = {
  question: "Question", bold_claim: "Bold Claim", listicle: "Listicle",
  story: "Story", none: "No Hook",
};

export function humanizeTopic(value: string): string {
  return value.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

export function label(dimension: string, value: string): string {
  if (dimension === "content_type") return CONTENT_TYPE_LABELS[value] ?? humanizeTopic(value);
  if (dimension === "platform") return PLATFORM_LABELS[value] ?? humanizeTopic(value);
  if (dimension === "hook_type") return HOOK_TYPE_LABELS[value] ?? humanizeTopic(value);
  return humanizeTopic(value);
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function signed(z: number): string {
  return `${z >= 0 ? "+" : ""}${z.toFixed(2)}`;
}

/**
 * Conclusion -> metric -> sample size, per the human-readable requirement.
 * Never renders raw "n=" notation. z is a standard-deviation-from-baseline
 * value (see PRD §6.2) — never rescaled to a 0-10 score or percentage here.
 */
export function describePerformance(z: number, n: number): {
  direction: "above" | "below" | "even";
  sdLine: string;
  postsLine: string;
} {
  const magnitude = Math.abs(z).toFixed(2);
  let direction: "above" | "below" | "even" = "even";
  let sdLine = `At your baseline: ${z.toFixed(2)} SD`;
  if (z > 0.05) {
    direction = "above";
    sdLine = `Above your baseline: +${magnitude} SD`;
  } else if (z < -0.05) {
    direction = "below";
    sdLine = `Below your baseline: -${magnitude} SD`;
  }
  return { direction, sdLine, postsLine: `Based on ${n} post${n === 1 ? "" : "s"}` };
}