import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.database import Base

PLATFORMS = ("youtube", "youtube_shorts", "instagram", "tiktok", "x", "linkedin")
CONTENT_TYPES = ("short_video", "long_video", "image", "carousel", "text")
HOOK_TYPES = ("question", "bold_claim", "listicle", "story", "none")

class UserBaseline(Base):
    __tablename__ = "user_baselines"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    platform = Column(Text, primary_key=True)
    content_type = Column(Text, primary_key=True)
    rolling_median_perf = Column(Float, nullable=True)
    p25 = Column(Float, nullable=True)
    p75 = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(f"platform IN {PLATFORMS}", name="ck_user_baselines_platform"),
        CheckConstraint(f"content_type IN {CONTENT_TYPES}", name="ck_user_baselines_content_type"),
    )

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    niche = Column(Text, nullable=False)
    goal = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    channels = relationship("Channel", back_populates="user", cascade="all, delete-orphan")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(Text, nullable=False)
    handle = Column(Text, nullable=False)
    follower_count = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(f"platform IN {PLATFORMS}", name="ck_channels_platform"),
    )

    user = relationship("User", back_populates="channels")
    content = relationship("Content", back_populates="channel", cascade="all, delete-orphan")


class Content(Base):
    __tablename__ = "content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    content_type = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)
    hashtags = Column(ARRAY(Text), nullable=True)
    topic_tags = Column(ARRAY(Text), nullable=True)
    hook_type = Column(Text, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=False, index=True)
    caption_embedding = Column(Vector(384), nullable=True)

    __table_args__ = (
        CheckConstraint(f"content_type IN {CONTENT_TYPES}", name="ck_content_content_type"),
        CheckConstraint(f"hook_type IN {HOOK_TYPES} OR hook_type IS NULL", name="ck_content_hook_type"),
    )

    channel = relationship("Channel", back_populates="content")
    metrics = relationship("Metric", back_populates="content", cascade="all, delete-orphan")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)
    captured_at = Column(DateTime(timezone=True), nullable=False, index=True)
    impressions = Column(Integer, nullable=True)
    reach = Column(Integer, nullable=True)
    views = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    shares = Column(Integer, nullable=True)
    saves = Column(Integer, nullable=True)
    watch_time_sec = Column(Integer, nullable=True)
    avg_pct_watched = Column(Float, nullable=True)
    followers_gained = Column(Integer, nullable=True)

    content = relationship("Content", back_populates="metrics")