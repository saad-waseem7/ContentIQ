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

export interface RecommendationHistoryResponse {
  user_id: string;
  count: number;
  recommendations: RecommendationResponse[];
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
  user_n: number;
  niche_other_users_n: number;
  niche_total_posts_n: number;
  user_median_engagement_rate?: number;
  niche_median_engagement_rate?: number;
  engagement_ratio?: number;
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

export interface PredictRequest {
  hook_type: string; content_type: string; platform: string;
  primary_topic_tag: string; duration_sec?: number | null; sample_caption: string;
}
export interface PredictResponse { predicted_score: number; topic_recognized?: boolean; }

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
      const d = body.detail;
      if (typeof d === "string" && d) {
        detail = d;
      } else if (Array.isArray(d)) {
        // FastAPI validation errors arrive as a list of { msg, loc, ... } objects.
        detail = d.map((item) => item?.msg).filter(Boolean).join("; ") || detail;
      }
    } catch {
      // response wasn't JSON — keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

// Full-URL keys keep users' responses separate; the short TTL bounds staleness
// for changes outside this client, while in-flight requests are deduplicated.
// Mutations invalidate affected history immediately.
const CACHE_TTL_MS = 30_000;
const _requestCache = new Map<string, { timestamp: number; data: unknown }>();
const _inFlight = new Map<string, Promise<unknown>>();

export function invalidateCache(prefix: string): void {
  for (const key of _requestCache.keys()) {
    if (key.startsWith(prefix)) _requestCache.delete(key);
  }
  for (const key of _inFlight.keys()) {
    if (key.startsWith(prefix)) _inFlight.delete(key);
  }
}

// Clear both maps between tests so cached state cannot leak across cases.
export function clearApiCache(): void {
  _requestCache.clear();
  _inFlight.clear();
}

async function cachedGet<T>(url: string): Promise<T> {
  const cached = _requestCache.get(url);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return cached.data as T;
  }

  const inFlight = _inFlight.get(url);
  if (inFlight) return inFlight as Promise<T>;

  const promise = fetch(url)
    .then((res) => handle<T>(res))
    .then((data) => {
      _requestCache.set(url, { timestamp: Date.now(), data });
      _inFlight.delete(url);
      return data;
    })
    .catch((err) => {
      _inFlight.delete(url);
      throw err;
    });

  _inFlight.set(url, promise);
  return promise as Promise<T>;
}

export async function getLeaderboard(userId: string): Promise<LeaderboardResponse> {
  return cachedGet<LeaderboardResponse>(`${BASE_URL}/content?user_id=${encodeURIComponent(userId)}`);
}

export async function getInsights(userId: string): Promise<InsightsResponse> {
  return cachedGet<InsightsResponse>(`${BASE_URL}/insights?user_id=${encodeURIComponent(userId)}`);
}

export async function getRecommendationHistory(userId: string): Promise<RecommendationHistoryResponse> {
  return cachedGet<RecommendationHistoryResponse>(`${BASE_URL}/recommendations?user_id=${encodeURIComponent(userId)}`);
}

export async function generateRecommendation(userId: string): Promise<RecommendationResponse> {
  const res = await fetch(`${BASE_URL}/recommend?user_id=${encodeURIComponent(userId)}`, { method: "POST" });
  const data = await handle<RecommendationResponse>(res);
  // A new recommendation changes this user's history — invalidate so the
  // next History visit reflects it instead of showing stale cached data.
  invalidateCache(`${BASE_URL}/recommendations?user_id=${encodeURIComponent(userId)}`);
  return data;
}

export async function submitFeedback(recommendationId: string, status: "actioned" | "dismissed"): Promise<RecommendationResponse> {
  const res = await fetch(`${BASE_URL}/recommendations/${recommendationId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  const data = await handle<RecommendationResponse>(res);
  // Status changed — invalidate ALL cached history entries (we don't know
  // which user this recommendation belongs to from here without another
  // call, and this is cheap/safe to do broadly).
  invalidateCache(`${BASE_URL}/recommendations?`);
  return data;
}

export async function predictIdea(userId: string, payload: PredictRequest): Promise<PredictResponse> {
  const res = await fetch(`${BASE_URL}/predict?user_id=${encodeURIComponent(userId)}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  return handle<PredictResponse>(res);
}