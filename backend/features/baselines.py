import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from features.common import compute_performance_raw

from app import models
from app.crud import upsert_user_baseline

# A (user, platform, content_type) group needs at least this many posts before
# its median/p25/p75 mean anything — 1-2 data points produce a meaningless "quartile."
# Not specified by the PRD; picked as the smallest number where a quartile split isn't degenerate.
MIN_POSTS_FOR_BASELINE = 3


def _load_latest_metric_per_content(db: Session) -> pd.DataFrame:
    """
    One row per content: its user_id/platform (via channel), content_type, and its
    most recent metric snapshot. Content with zero metric rows is excluded —
    there's nothing to compute a baseline from yet.
    """
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
        columns=["content_id", "content_type", "user_id", "platform", "captured_at",
                 "likes", "comments", "shares", "saves", "reach"],
    )
    if df.empty:
        return df

    for col in ("likes", "comments", "shares", "saves", "reach"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep only the latest snapshot per content_id — a post's most mature/cumulative
    # performance is what should feed the baseline, not an early partial reading.
    df = df.sort_values("captured_at").groupby("content_id", as_index=False).tail(1)
    return df


# def _compute_performance_raw(df: pd.DataFrame) -> pd.DataFrame:
#     """performance_raw = (likes+comments+shares+saves) / reach, per PRD. Rows with
#     zero or NULL reach can't produce a ratio (NULLIF-equivalent) and are dropped."""
#     engagement = df[["likes", "comments", "shares", "saves"]].fillna(0).sum(axis=1)
#     reach = df["reach"].replace(0, np.nan)
#     df = df.assign(performance_raw=engagement / reach)
#     return df.dropna(subset=["performance_raw"])


def compute_and_store_baselines(db: Session) -> int:
    """Computes the CURRENT (all-history) baseline per (user, platform, content_type)
    and upserts it into user_baselines. This is a serving-time snapshot, not used
    for leakage-safe training labels — see the feature builder for that."""
    df = _load_latest_metric_per_content(db)
    if df.empty:
        return 0

    df = compute_performance_raw(df)

    stats = (
        df.groupby(["user_id", "platform", "content_type"])["performance_raw"]
        .agg(rolling_median_perf="median", p25=lambda s: s.quantile(0.25), p75=lambda s: s.quantile(0.75), n="count")
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