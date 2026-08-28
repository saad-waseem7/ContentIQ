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

export interface DimensionEntry {
  value: string;
  n: number;
  mean_performance_z: number;
  is_standout: boolean;
}

export interface TrendInsight {
  sufficient_data: boolean;
  recent_period_days?: number;
  recent_mean_performance_z?: number;
  recent_n?: number;
  historical_mean_performance_z?: number;
  historical_n?: number;
  direction: string;
  note: string;
}

export interface MonthlyPerformanceEntry {
  period: string;
  mean_performance_z: number;
  n: number;
}

export interface NicheComparison {
  sufficient_data: boolean;
  user_mean_performance_z?: number;
  user_n: number;
  niche_mean_performance_z?: number;
  niche_other_users_n: number;
  niche_total_posts_n: number;
  delta?: number;
}

export interface NichePatternEntry {
  dimension: string;
  value: string;
  n: number;
  mean_performance_z: number;
  is_standout: boolean;
}

export interface ClusterEntry {
  cluster_id: number;
  n: number;
  mean_performance_z: number;
  dominant_content_type: string;
  dominant_hook_type: string;
  dominant_topic_tag: string;
  is_high_performing: boolean;
}

export interface TopicClusters {
  available: boolean;
  reason_unavailable?: string;
  k?: number;
  silhouette_score?: number;
  clusters?: ClusterEntry[];
  user_cluster_summary: { cluster_id: number; user_post_count: number }[];
}

export interface InsightsResponse {
  user_id: string;
  niche: string;
  personal_patterns: { total_posts_analyzed: number; dimensions: Record<string, DimensionEntry[]> };
  trend: TrendInsight;
  monthly_performance: MonthlyPerformanceEntry[];
  niche_comparison: NicheComparison;
  niche_top_patterns: NichePatternEntry[];
  topic_clusters: TopicClusters;
}

export async function getInsights(userId: string): Promise<InsightsResponse> {
  const res = await fetch(`${BASE_URL}/insights?user_id=${encodeURIComponent(userId)}`);
  return handle<InsightsResponse>(res);
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