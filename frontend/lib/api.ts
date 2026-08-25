// Types mirror backend/app/schemas.py exactly — verified against the actual
// Pydantic models, not assumed from endpoint names.

export interface LeaderboardEntry {
  rank: number;
  content_id: string;
  platform: string;
  content_type: string;
  hook_type: string | null;
  topic_tags: string[];
  posted_at: string;
  performance_raw: number;
  performance_z: number;
  is_top_performer: boolean;
}

export interface LeaderboardResponse {
  user_id: string;
  niche: string;
  total_posts_in_history: number;
  ranked_posts: number;
  leaderboard: LeaderboardEntry[];
}

export interface RecommendationResponse {
  id: string;
  idea_text: string;
  format: string;
  best_time: string | null;
  rationale: string;
  predicted_score: number;
  status: string;
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON — keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

export async function getLeaderboard(userId: string): Promise<LeaderboardResponse> {
  const res = await fetch(`${BASE_URL}/content?user_id=${encodeURIComponent(userId)}`);
  return handle<LeaderboardResponse>(res);
}

export async function generateRecommendation(userId: string): Promise<RecommendationResponse> {
  const res = await fetch(`${BASE_URL}/recommend?user_id=${encodeURIComponent(userId)}`, {
    method: "POST",
  });
  return handle<RecommendationResponse>(res);
}

export async function submitFeedback(
  recommendationId: string,
  status: "actioned" | "dismissed"
): Promise<RecommendationResponse> {
  const res = await fetch(`${BASE_URL}/recommendations/${recommendationId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  return handle<RecommendationResponse>(res);
}