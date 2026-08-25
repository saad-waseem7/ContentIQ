import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

PLATFORMS = {"youtube", "youtube_shorts", "instagram", "tiktok", "x", "linkedin"}
CONTENT_TYPES = {"short_video", "long_video", "image", "carousel", "text"}
HOOK_TYPES = {"question", "bold_claim", "listicle", "story", "none"}


class UserIngest(BaseModel):
    id: Optional[uuid.UUID] = None
    niche: str
    goal: Optional[str] = None


class ChannelIngest(BaseModel):
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    platform: str
    handle: str
    follower_count: Optional[int] = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in PLATFORMS:
            raise ValueError(f"platform must be one of {sorted(PLATFORMS)}")
        return v


class MetricIngest(BaseModel):
    captured_at: datetime
    impressions: Optional[int] = None
    reach: Optional[int] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    watch_time_sec: Optional[int] = None
    avg_pct_watched: Optional[float] = None
    followers_gained: Optional[int] = None


class ContentIngest(BaseModel):
    id: Optional[uuid.UUID] = None
    channel_id: uuid.UUID
    content_type: str
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[list[str]] = None
    topic_tags: Optional[list[str]] = None
    hook_type: Optional[str] = None
    duration_sec: Optional[int] = None
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
            if m.captured_at < self.posted_at:
                raise ValueError("metric captured_at cannot be before content posted_at")
        return self


class IngestRequest(BaseModel):
    user: Optional[UserIngest] = None
    channel: Optional[ChannelIngest] = None
    content: Optional[ContentIngest] = None

    @model_validator(mode="after")
    def at_least_one_present(self):
        if self.user is None and self.channel is None and self.content is None:
            raise ValueError("at least one of user, channel, or content must be provided")
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
