import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from app.models import PLATFORMS, CONTENT_TYPES, HOOK_TYPES

# Bound user-controlled text and tag counts at the ingestion boundary.
MAX_SHORT_TEXT = 200      # niche, handle, topic tags, hashtags
MAX_TITLE_TEXT = 300      # content title
MAX_GOAL_TEXT = 500       # creator goal
MAX_LONG_TEXT = 5000      # captions
MAX_TAG_LIST_ITEMS = 100  # hashtags / topic_tags per post

ShortText = Annotated[str, Field(max_length=MAX_SHORT_TEXT)]


class UserIngest(BaseModel):
    id: Optional[uuid.UUID] = None
    niche: str = Field(max_length=MAX_SHORT_TEXT)
    goal: Optional[str] = Field(default=None, max_length=MAX_GOAL_TEXT)


class ChannelIngest(BaseModel):
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    platform: str
    handle: str = Field(max_length=MAX_SHORT_TEXT)
    follower_count: Optional[int] = Field(default=None, ge=0)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in PLATFORMS:
            raise ValueError(f"platform must be one of {sorted(PLATFORMS)}")
        return v


def _as_utc(value: datetime) -> datetime:
    """Treats a naive datetime as UTC so naive and timezone-aware values can be compared."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class MetricIngest(BaseModel):
    captured_at: datetime
    impressions: Optional[int] = Field(default=None, ge=0)
    reach: Optional[int] = Field(default=None, ge=0)
    views: Optional[int] = Field(default=None, ge=0)
    likes: Optional[int] = Field(default=None, ge=0)
    comments: Optional[int] = Field(default=None, ge=0)
    shares: Optional[int] = Field(default=None, ge=0)
    saves: Optional[int] = Field(default=None, ge=0)
    watch_time_sec: Optional[int] = Field(default=None, ge=0)
    avg_pct_watched: Optional[float] = Field(default=None, ge=0)
    followers_gained: Optional[int] = None


class ContentIngest(BaseModel):
    id: Optional[uuid.UUID] = None
    channel_id: uuid.UUID
    content_type: str
    title: Optional[str] = Field(default=None, max_length=MAX_TITLE_TEXT)
    caption: Optional[str] = Field(default=None, max_length=MAX_LONG_TEXT)
    hashtags: Optional[list[ShortText]] = Field(default=None, max_length=MAX_TAG_LIST_ITEMS)
    topic_tags: Optional[list[ShortText]] = Field(default=None, max_length=MAX_TAG_LIST_ITEMS)
    hook_type: Optional[str] = None
    duration_sec: Optional[int] = Field(default=None, ge=0)
    posted_at: datetime
    metrics: list[MetricIngest] = Field(default_factory=list)

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        if v not in CONTENT_TYPES:
            raise ValueError(f"content_type must be one of {sorted(CONTENT_TYPES)}")
        return v

    @field_validator("hook_type")
    @classmethod
    def validate_hook_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in HOOK_TYPES:
            raise ValueError(f"hook_type must be one of {sorted(HOOK_TYPES)}")
        return v

    @model_validator(mode="after")
    def metrics_not_before_posted_at(self):
        for m in self.metrics:
            if _as_utc(m.captured_at) < _as_utc(self.posted_at):
                raise ValueError(
                    "metric captured_at cannot be before content posted_at"
                )
        return self


class IngestRequest(BaseModel):
    user: Optional[UserIngest] = None
    channel: Optional[ChannelIngest] = None
    content: Optional[ContentIngest] = None

    @model_validator(mode="after")
    def at_least_one_present(self):
        if self.user is None and self.channel is None and self.content is None:
            raise ValueError(
                "at least one of user, channel, or content must be provided"
            )
        return self


class IngestResponse(BaseModel):
    user_id: Optional[uuid.UUID] = None
    channel_id: Optional[uuid.UUID] = None
    content_id: Optional[uuid.UUID] = None
    metrics_created: int = 0


class LeaderboardEntry(BaseModel):
    rank: int
    content_id: str
    platform: str
    content_type: str
    hook_type: Optional[str] = None
    topic_tags: list[str] = Field(default_factory=list)
    posted_at: datetime
    performance_raw: float
    performance_z: float
    is_top_performer: bool


class LeaderboardResponse(BaseModel):
    user_id: str
    niche: str
    total_posts_in_history: int
    ranked_posts: int
    leaderboard: list[LeaderboardEntry]


class RecommendationResponse(BaseModel):
    id: str
    idea_text: str
    format: str
    best_time: Optional[str] = None
    rationale: str
    predicted_score: float
    status: str
    created_at: datetime


class FeedbackRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        if v not in ("actioned", "dismissed"):
            raise ValueError("status must be 'actioned' or 'dismissed'")
        return v


class DimensionEntry(BaseModel):
    value: str
    n: int
    mean_performance_z: float
    is_standout: bool


class PersonalPatterns(BaseModel):
    total_posts_analyzed: int
    dimensions: dict[str, list[DimensionEntry]]


class TrendInsight(BaseModel):
    sufficient_data: bool
    recent_period_days: Optional[int] = None
    recent_mean_performance_z: Optional[float] = None
    recent_n: Optional[int] = None
    historical_mean_performance_z: Optional[float] = None
    historical_n: Optional[int] = None
    direction: str
    note: str


class MonthlyPerformanceEntry(BaseModel):
    period: str
    mean_performance_z: float
    n: int


class NicheComparison(BaseModel):
    sufficient_data: bool
    user_n: int
    niche_other_users_n: int
    niche_total_posts_n: int
    user_median_engagement_rate: Optional[float] = None
    niche_median_engagement_rate: Optional[float] = None
    engagement_ratio: Optional[float] = None


class NichePatternEntry(BaseModel):
    dimension: str
    value: str
    n: int
    mean_performance_z: float
    is_standout: bool


class ClusterEntry(BaseModel):
    cluster_id: int
    n: int
    mean_performance_z: float
    dominant_content_type: str
    dominant_hook_type: str
    dominant_topic_tag: str
    is_high_performing: bool


class UserClusterSummaryEntry(BaseModel):
    cluster_id: int
    user_post_count: int


class TopicClusters(BaseModel):
    available: bool
    reason_unavailable: Optional[str] = None
    k: Optional[int] = None
    silhouette_score: Optional[float] = None
    clusters: Optional[list[ClusterEntry]] = None
    user_cluster_summary: list[UserClusterSummaryEntry] = Field(default_factory=list)


class InsightsResponse(BaseModel):
    user_id: str
    niche: str
    personal_patterns: PersonalPatterns
    trend: TrendInsight
    monthly_performance: list[MonthlyPerformanceEntry]
    niche_comparison: NicheComparison
    niche_top_patterns: list[NichePatternEntry]
    topic_clusters: TopicClusters


class PredictRequest(BaseModel):
    hook_type: str
    content_type: str
    platform: str
    primary_topic_tag: str = Field(max_length=MAX_SHORT_TEXT)
    duration_sec: Optional[int] = Field(default=None, ge=0)
    sample_caption: str = Field(max_length=MAX_LONG_TEXT)

    @field_validator("hook_type")
    @classmethod
    def check_hook_type(cls, v):
        if v not in HOOK_TYPES:
            raise ValueError(f"hook_type must be one of {HOOK_TYPES}")
        return v

    @field_validator("content_type")
    @classmethod
    def check_content_type(cls, v):
        if v not in CONTENT_TYPES:
            raise ValueError(f"content_type must be one of {CONTENT_TYPES}")
        return v

    @field_validator("platform")
    @classmethod
    def check_platform(cls, v):
        if v not in PLATFORMS:
            raise ValueError(f"platform must be one of {PLATFORMS}")
        return v

    @field_validator("sample_caption", "primary_topic_tag")
    @classmethod
    def check_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("field must not be empty")
        return v


class PredictResponse(BaseModel):
    predicted_score: float
    topic_recognized: bool = True

class RecommendationHistoryResponse(BaseModel):
    user_id: str
    count: int
    recommendations: list[RecommendationResponse]