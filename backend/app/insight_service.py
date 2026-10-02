"""
Week 6 Insight Engine — user-level, time-series, and niche-comparison
sections. Deterministic aggregation only; no LLM calls in this module.
Reuses the exact has_sufficient_group_history + non-null performance_z
definition of "valid" established in Week 3/4 rather than inventing a
new one.
"""
from datetime import timedelta

import pandas as pd

from app import insight_clustering
from app import insight_config as cfg
from app.leaderboard_service import load_feature_table, UnknownUserError


def _add_primary_topic(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["primary_topic_tag"] = df["topic_tags"].apply(
        lambda t: t[0] if t is not None and len(t) > 0 else "none"
    )
    return df


def _add_time_window(df: pd.DataFrame) -> pd.DataFrame:
    def bucket(hour):
        for name, hrs in cfg.TIME_WINDOWS:
            if hour in hrs:
                return name
        return "unknown"
    df = df.copy()
    df["posting_time_window"] = df["posting_hour"].apply(bucket)
    return df


def _valid_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["has_sufficient_group_history"] & df["performance_z"].notna()]


def _dimension_breakdown(df_valid: pd.DataFrame, column: str, min_n: int) -> list[dict]:
    if df_valid.empty or column not in df_valid.columns:
        return []
    grouped = df_valid.groupby(column)["performance_z"].agg(["mean", "count"]).reset_index()
    grouped = grouped[grouped["count"] >= min_n].sort_values("mean", ascending=False)
    return [
        {
            "value": row[column],
            "n": int(row["count"]),
            "mean_performance_z": round(float(row["mean"]), 3),
            "is_standout": bool(row["mean"] > 0.5),
        }
        for _, row in grouped.iterrows()
    ]


def personal_pattern_insights(user_df: pd.DataFrame) -> dict:
    df_valid = _valid_rows(_add_time_window(_add_primary_topic(user_df)))
    # content_type is deliberately not a dimension: performance_z is normalized within each
    # (platform, content_type) group, so its mean is ~0 for every content type by construction
    # and says nothing about which format performs better. The other dimensions cross-cut
    # those groups, so their means are meaningful.
    return {
        "total_posts_analyzed": int(len(df_valid)),
        "dimensions": {
            "hook_type": _dimension_breakdown(df_valid, "hook_type", cfg.PERSONAL_PATTERN_MIN_N),
            "topic": _dimension_breakdown(df_valid, "primary_topic_tag", cfg.PERSONAL_PATTERN_MIN_N),
            "posting_time_window": _dimension_breakdown(df_valid, "posting_time_window", cfg.PERSONAL_PATTERN_MIN_N),
        },
    }


def trend_insights(user_df: pd.DataFrame) -> dict:
    note = "Descriptive only — reflects what happened, not why."
    df_valid = _valid_rows(user_df)
    if df_valid.empty:
        return {"sufficient_data": False, "direction": "insufficient_data", "note": note}

    df_valid = df_valid.sort_values("posted_at")
    most_recent = df_valid["posted_at"].max()
    cutoff = most_recent - timedelta(days=cfg.TREND_RECENT_WINDOW_DAYS)

    recent = df_valid[df_valid["posted_at"] > cutoff]
    historical = df_valid[df_valid["posted_at"] <= cutoff]

    if len(recent) < cfg.TREND_MIN_N_PER_PERIOD or len(historical) < cfg.TREND_MIN_N_PER_PERIOD:
        return {
            "sufficient_data": False, "recent_n": int(len(recent)), "historical_n": int(len(historical)),
            "direction": "insufficient_data", "note": note,
        }

    recent_mean = float(recent["performance_z"].mean())
    historical_mean = float(historical["performance_z"].mean())
    delta = recent_mean - historical_mean
    direction = "improving" if delta > cfg.TREND_DIRECTION_THRESHOLD else (
        "declining" if delta < -cfg.TREND_DIRECTION_THRESHOLD else "stable"
    )

    return {
        "sufficient_data": True, "recent_period_days": cfg.TREND_RECENT_WINDOW_DAYS,
        "recent_mean_performance_z": round(recent_mean, 3), "recent_n": int(len(recent)),
        "historical_mean_performance_z": round(historical_mean, 3), "historical_n": int(len(historical)),
        "direction": direction, "note": note,
    }


def monthly_performance(user_df: pd.DataFrame) -> list[dict]:
    df_valid = _valid_rows(user_df)
    if df_valid.empty:
        return []
    df_valid = df_valid.copy()
    df_valid["period"] = pd.to_datetime(df_valid["posted_at"]).dt.strftime("%Y-%m")
    grouped = df_valid.groupby("period")["performance_z"].agg(["mean", "count"]).reset_index()
    grouped = grouped[grouped["count"] >= cfg.MONTHLY_MIN_N].sort_values("period")
    return [
        {"period": row["period"], "mean_performance_z": round(float(row["mean"]), 3), "n": int(row["count"])}
        for _, row in grouped.iterrows()
    ]


def niche_comparison(user_df: pd.DataFrame, niche_df: pd.DataFrame, user_id: str) -> dict:
    """Compares absolute engagement rate (performance_raw) with other creators' posts of the
    same platform and content type.

    performance_z cannot be used here: it is measured against each creator's own history, so
    its mean is ~0 for every creator whether they perform well or badly.
    """
    user_valid = _valid_rows(user_df)
    others_valid = _valid_rows(niche_df[niche_df["user_id"] != user_id])
    other_user_count = others_valid["user_id"].nunique()

    base = {
        "user_n": int(len(user_valid)),
        "niche_other_users_n": int(other_user_count),
        "niche_total_posts_n": int(len(others_valid)),
    }
    insufficient = {"sufficient_data": False, **base}
    if (
        user_valid.empty
        or other_user_count < cfg.NICHE_COMPARISON_MIN_OTHER_USERS
        or len(others_valid) < cfg.NICHE_COMPARISON_MIN_TOTAL_POSTS
    ):
        return insufficient

    group_cols = ["platform", "content_type"]
    niche_medians = others_valid.groupby(group_cols)["performance_raw"].median().rename("niche_group_median")
    comparable = user_valid.join(niche_medians, on=group_cols).dropna(subset=["niche_group_median"])
    if len(comparable) < cfg.PERSONAL_PATTERN_MIN_N:
        return insufficient

    user_median = float(comparable["performance_raw"].median())
    niche_median = float(comparable["niche_group_median"].median())
    if niche_median <= 0:
        return insufficient

    return {
        "sufficient_data": True,
        "user_median_engagement_rate": round(user_median, 4),
        "niche_median_engagement_rate": round(niche_median, 4),
        "engagement_ratio": round(user_median / niche_median, 3),
        **{**base, "user_n": int(len(comparable))},
    }


def niche_top_patterns(niche_df: pd.DataFrame) -> list[dict]:
    df_valid = _valid_rows(_add_primary_topic(niche_df))
    results = []
    # Same reason as personal_pattern_insights: content_type means are ~0 by construction.
    for dim in ("hook_type", "primary_topic_tag"):
        for entry in _dimension_breakdown(df_valid, dim, cfg.NICHE_PATTERN_MIN_N):
            results.append({"dimension": dim, **entry})
    results.sort(key=lambda r: r["mean_performance_z"], reverse=True)
    return results[: cfg.NICHE_PATTERN_TOP_K]


def build_user_niche_frames(user_id: str) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    df_all = load_feature_table()
    user_df = df_all[df_all["user_id"] == user_id]
    if user_df.empty:
        raise UnknownUserError(f"No content found for user_id {user_id}")
    niche = user_df["niche"].iloc[0]
    niche_df = df_all[df_all["niche"] == niche]
    return user_df, niche_df, niche


def build_insights(db, user_id: str) -> dict:
    user_df, niche_df, niche = build_user_niche_frames(user_id)

    niche_df_valid_topic = _valid_rows(_add_primary_topic(niche_df))
    cluster_result, label_df = insight_clustering.load_and_compute_niche_clusters(db, niche, niche_df_valid_topic)
    cluster_result["user_cluster_summary"] = (
        insight_clustering.build_user_cluster_summary(label_df, user_df["content_id"].tolist())
        if cluster_result.get("available") else []
    )

    return {
        "user_id": user_id,
        "niche": niche,
        "personal_patterns": personal_pattern_insights(user_df),
        "trend": trend_insights(user_df),
        "monthly_performance": monthly_performance(user_df),
        "niche_comparison": niche_comparison(user_df, niche_df, user_id),
        "niche_top_patterns": niche_top_patterns(niche_df),
        "topic_clusters": cluster_result,
    }