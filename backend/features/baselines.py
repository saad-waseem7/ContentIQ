import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from features.common import compute_performance_raw

from app import models
from app.crud import upsert_user_baseline

# Require three observations before storing group quartiles.
MIN_POSTS_FOR_BASELINE = 3


def _load_latest_metric_per_content(db: Session) -> pd.DataFrame:
    """Return one row per post using its latest metrics; omit posts without metrics."""
    rows = db.execute(
        select(
            models.Content.id.label("content_id"),
            models.Content.content_type,
            models.Channel.user_id,
            models.Channel.platform,
            models.Metric.captured_at,
            models.Metric.likes,
            models.Metric.comments,
            models.Metric.shares,
            models.Metric.saves,
            models.Metric.reach,
        )
        .join(models.Channel, models.Content.channel_id == models.Channel.id)
        .join(models.Metric, models.Metric.content_id == models.Content.id)
    ).all()

    df = pd.DataFrame(
        rows,
        columns=[
            "content_id",
            "content_type",
            "user_id",
            "platform",
            "captured_at",
            "likes",
            "comments",
            "shares",
            "saves",
            "reach",
        ],
    )
    if df.empty:
        return df

    for col in ("likes", "comments", "shares", "saves", "reach"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Use each post's latest snapshot so baselines reflect the most recent metrics available.
    df = df.sort_values("captured_at").groupby("content_id", as_index=False).tail(1)
    return df


def compute_and_store_baselines(db: Session) -> int:
    """Upsert all-history baselines for serving; training labels use prior-only feature baselines."""
    df = _load_latest_metric_per_content(db)
    if df.empty:
        return 0

    df = compute_performance_raw(df)

    stats = (
        df.groupby(["user_id", "platform", "content_type"])["performance_raw"]
        .agg(
            rolling_median_perf="median",
            p25=lambda s: s.quantile(0.25),
            p75=lambda s: s.quantile(0.75),
            n="count",
        )
        .reset_index()
    )
    stats = stats[stats["n"] >= MIN_POSTS_FOR_BASELINE]

    for _, row in stats.iterrows():
        upsert_user_baseline(
            db,
            user_id=row["user_id"],
            platform=row["platform"],
            content_type=row["content_type"],
            rolling_median_perf=float(row["rolling_median_perf"]),
            p25=float(row["p25"]),
            p75=float(row["p75"]),
        )

    return len(stats)
