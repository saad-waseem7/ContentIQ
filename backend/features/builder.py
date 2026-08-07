"""
Feature table builder (Week 3).

Produces one row per content post using ONLY information available strictly
before that post's posted_at, per PRD (leakage guard).

Split into two layers deliberately:
  - `_load_raw_data(db)` / `_load_embeddings(db)` — DB I/O, returns plain DataFrames/dicts.
  - `compute_feature_table(raw_df, embeddings)` — pure function, zero DB access.
    This split exists so the leakage unit test can call the pure function
    directly on a small synthetic DataFrame, with no live database needed.
"""
import uuid

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
import features.content_features as cf
import features.config as cfg
from features.common import compute_performance_raw


def _load_raw_data(db: Session) -> pd.DataFrame:
    content_rows = db.execute(
        select(
            models.Content.id.label("content_id"),
            models.Content.content_type,
            models.Content.title,
            models.Content.caption,
            models.Content.hashtags,
            models.Content.topic_tags,
            models.Content.hook_type,
            models.Content.duration_sec,
            models.Content.posted_at,
            models.Channel.user_id,
            models.Channel.platform,
            models.Channel.follower_count,
            models.User.niche,
        )
        .join(models.Channel, models.Content.channel_id == models.Channel.id)
        .join(models.User, models.Channel.user_id == models.User.id)
    ).all()
    content_df = pd.DataFrame(content_rows, columns=[
        "content_id", "content_type", "title", "caption", "hashtags", "topic_tags", "hook_type",
        "duration_sec", "posted_at", "user_id", "platform", "follower_count", "niche",
    ])
    metric_rows = db.execute(
        select(
            models.Metric.content_id, models.Metric.captured_at,
            models.Metric.likes, models.Metric.comments, models.Metric.shares,
            models.Metric.saves, models.Metric.reach,
        )
    ).all()
    metrics_df = pd.DataFrame(metric_rows, columns=[
        "content_id", "captured_at", "likes", "comments", "shares", "saves", "reach",
    ])
    metrics_df = metrics_df.sort_values("captured_at").groupby("content_id", as_index=False).tail(1)

    return content_df.merge(metrics_df, on="content_id", how="inner")


def _load_embeddings(db: Session) -> dict[uuid.UUID, np.ndarray]:
    rows = db.execute(
        select(models.Content.id, models.Content.caption_embedding)
        .where(models.Content.caption_embedding.is_not(None))
    ).all()
    return {content_id: np.array(vec, dtype=float) for content_id, vec in rows}


def _compute_expanding_group_stats(df: pd.DataFrame) -> pd.DataFrame:
    """performance_z and label_overperformer per (user, platform, content_type),
    using only strictly prior posts in that same group. Explicit loop, see
    module-level docstring / Checkpoint 14 design note for why."""
    df = df.sort_values(["user_id", "platform", "content_type", "posted_at"]).reset_index(drop=True)

    z_scores = pd.Series(index=df.index, dtype=float)
    labels = pd.Series(index=df.index, dtype=object)
    has_history = pd.Series(index=df.index, dtype=bool)

    for _, group in df.groupby(["user_id", "platform", "content_type"], sort=False):
        history: list[float] = []
        for idx, row in group.iterrows():
            if len(history) >= cfg.MIN_GROUP_SIZE_FOR_ZSCORE:
                mean = np.mean(history)
                std = np.std(history, ddof=1)
                p75 = np.percentile(history, 75)
                z_scores[idx] = (row["performance_raw"] - mean) / std if std > 0 else 0.0
                labels[idx] = bool(row["performance_raw"] > p75)
                has_history[idx] = True
            else:
                z_scores[idx] = np.nan
                labels[idx] = np.nan
                has_history[idx] = False
            history.append(row["performance_raw"])

    df["performance_z"] = z_scores
    df["label_overperformer"] = labels
    df["has_sufficient_group_history"] = has_history
    return df


def _compute_user_context_features(df: pd.DataFrame) -> pd.DataFrame:
    """days_since_last_post and content_type_share_recent, per user across all
    their content (not scoped to platform/content_type — this models general
    posting cadence, a different concept than the performance-normalization grouping)."""
    df = df.sort_values(["user_id", "posted_at"]).reset_index(drop=True)

    days_since_last = pd.Series(index=df.index, dtype=float)
    is_first_post = pd.Series(index=df.index, dtype=bool)
    content_type_share = pd.Series(index=df.index, dtype=float)

    for _, group in df.groupby("user_id", sort=False):
        recent_types: list[str] = []
        prev_posted_at = None
        for idx, row in group.iterrows():
            if prev_posted_at is None:
                days_since_last[idx] = np.nan
                is_first_post[idx] = True
            else:
                days_since_last[idx] = (row["posted_at"] - prev_posted_at).total_seconds() / 86400
                is_first_post[idx] = False

            window = recent_types[-cfg.RECENT_POSTS_WINDOW:]
            content_type_share[idx] = window.count(row["content_type"]) / len(window) if window else np.nan

            recent_types.append(row["content_type"])
            prev_posted_at = row["posted_at"]

    df["days_since_last_post"] = days_since_last
    df["is_first_post_for_user"] = is_first_post
    df["content_type_share_recent"] = content_type_share
    return df


def _compute_semantic_similarity_feature(df: pd.DataFrame, embeddings: dict) -> pd.DataFrame:
    """Cosine similarity between this post's embedding and the centroid of the
    SAME user's prior posts labeled overperformer. Requires label_overperformer
    already computed (leakage-safe) — this feature inherits that guarantee since
    it only ever looks at strictly prior posts too."""
    df = df.sort_values(["user_id", "posted_at"]).reset_index(drop=True)
    similarity = pd.Series(index=df.index, dtype=float)

    for _, group in df.groupby("user_id", sort=False):
        prior_winners: list[np.ndarray] = []
        for idx, row in group.iterrows():
            own_vec = embeddings.get(row["content_id"])
            if own_vec is not None and prior_winners:
                centroid = np.mean(prior_winners, axis=0)
                c_norm, o_norm = np.linalg.norm(centroid), np.linalg.norm(own_vec)
                similarity[idx] = float(np.dot(own_vec, centroid) / (c_norm * o_norm)) if c_norm > 0 and o_norm > 0 else np.nan
            else:
                similarity[idx] = np.nan

            if own_vec is not None and row.get("label_overperformer") is True:
                prior_winners.append(own_vec)

    df["similarity_to_prior_winners"] = similarity
    return df


def _apply_content_features(df: pd.DataFrame) -> pd.DataFrame:
    df["caption_length_chars"] = df["caption"].apply(cf.caption_length_chars)
    df["caption_length_words"] = df["caption"].apply(cf.caption_length_words)
    df["hashtag_count"] = df["hashtags"].apply(cf.hashtag_count)
    df["emoji_count"] = df["caption"].apply(cf.emoji_count)
    df["has_cta"] = df["caption"].apply(cf.has_cta)
    df["duration_bucket"] = df["duration_sec"].apply(cf.duration_bucket)
    df["posting_hour"] = df["posted_at"].apply(cf.posting_hour)
    df["posting_day_of_week"] = df["posted_at"].apply(cf.posting_day_of_week)
    df["is_weekend"] = df["posted_at"].apply(cf.is_weekend)
    df["sentiment_score"] = df["caption"].apply(cf.sentiment_score)
    df["follower_tier"] = df["follower_count"].apply(
        lambda x: pd.cut([x], bins=cfg.FOLLOWER_BUCKETS, labels=cfg.FOLLOWER_BUCKET_LABELS, right=False)[0]
        if pd.notna(x) else "unknown"
    )
    return df


def compute_feature_table(raw_df: pd.DataFrame, embeddings: dict) -> pd.DataFrame:
    """Pure function, no DB access — see module docstring."""
    df = raw_df.copy()
    df = compute_performance_raw(df)
    df = _compute_expanding_group_stats(df)
    df = _compute_user_context_features(df)
    df = _compute_semantic_similarity_feature(df, embeddings)
    df = _apply_content_features(df)
    return df


def build_feature_table(db: Session) -> pd.DataFrame:
    raw_df = _load_raw_data(db)
    embeddings = _load_embeddings(db)
    return compute_feature_table(raw_df, embeddings)