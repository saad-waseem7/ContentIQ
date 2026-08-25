from pathlib import Path
from typing import Optional

import pandas as pd

FEATURES_PATH = Path(__file__).resolve().parents[1] / "data" / "features.parquet"


class FeatureDataNotBuiltError(Exception):
    """features.parquet doesn't exist yet — run scripts/build_features.py."""


class UnknownUserError(Exception):
    """user_id has no rows in the feature table."""


def load_feature_table(features_path: Optional[Path] = None) -> pd.DataFrame:
    # Resolved at call time, not bind time — required so tests can monkeypatch
    # FEATURES_PATH and have it actually take effect on the next call.
    path = features_path if features_path is not None else FEATURES_PATH
    if not path.exists():
        raise FeatureDataNotBuiltError(
            f"Feature table not found at {path}. Run scripts/build_features.py first."
        )
    return pd.read_parquet(path)


def get_user_feature_rows(user_id: str, features_path: Optional[Path] = None) -> pd.DataFrame:
    """Raw, filtered (not yet ranked/serialized) rows for one user. Shared by
    build_leaderboard() and recommendation_service, which needs raw columns
    (follower_count, etc.) the leaderboard's response doesn't expose."""
    df = load_feature_table(features_path)
    user_df = df[df["user_id"] == user_id]
    if user_df.empty:
        raise UnknownUserError(f"No content found for user_id {user_id}")
    return user_df


def build_leaderboard(user_id: str, features_path: Optional[Path] = None) -> dict:
    user_df = get_user_feature_rows(user_id, features_path)

    total_posts_in_history = len(user_df)

    # Rows with no prior group history (first ~2 posts per user/platform/content_type,
    # per builder.py's MIN_GROUP_SIZE_FOR_ZSCORE) have no valid performance_z/label —
    # excluded from ranking rather than shown with a fabricated score.
    ranked_df = user_df[user_df["has_sufficient_group_history"]].copy()
    ranked_df = ranked_df.sort_values("performance_z", ascending=False).reset_index(drop=True)
    ranked_df["rank"] = ranked_df.index + 1

    # Safe: niche is a column on users, one row per user — verified against
    # models.py, not assumed. Every content row reaches niche via a single
    # unambiguous join path (content -> channel -> user), so this can't diverge.
    niche = user_df["niche"].iloc[0]

    leaderboard = [
        {
            "rank": int(row["rank"]),
            "content_id": row["content_id"],
            "platform": row["platform"],
            "content_type": row["content_type"],
            "hook_type": row["hook_type"],
            "topic_tags": list(row["topic_tags"]) if row["topic_tags"] is not None else [],
            "posted_at": row["posted_at"],
            "performance_raw": float(row["performance_raw"]),
            "performance_z": float(row["performance_z"]),
            "is_top_performer": bool(row["label_overperformer"]),
        }
        for _, row in ranked_df.iterrows()
    ]

    return {
        "user_id": user_id,
        "niche": niche,
        "total_posts_in_history": total_posts_in_history,
        "ranked_posts": len(ranked_df),
        "leaderboard": leaderboard,
    }