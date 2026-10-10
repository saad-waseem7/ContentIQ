import threading
from pathlib import Path
from typing import Optional

import pandas as pd

from features.config import MIN_PRIOR_POSTS_FOR_RANKING

FEATURES_PATH = Path(__file__).resolve().parents[1] / "data" / "features.parquet"


class FeatureDataNotBuiltError(Exception):
    """features.parquet is missing; run scripts/build_features.py."""


class UnknownUserError(Exception):
    """user_id has no rows in the feature table."""


# Cache parsed tables by resolved path and modification time. Path-scoped entries
# keep test fixtures separate; the lock protects concurrent cache access.
_feature_table_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_feature_table_cache_lock = threading.Lock()


def clear_feature_table_cache() -> None:
    """Clear cached feature tables so tests can verify a cold load."""
    with _feature_table_cache_lock:
        _feature_table_cache.clear()


def load_feature_table(features_path: Optional[Path] = None) -> pd.DataFrame:
    # Resolve the default at call time so tests can replace FEATURES_PATH.
    path = features_path if features_path is not None else FEATURES_PATH
    if not path.exists():
        raise FeatureDataNotBuiltError(
            f"Feature table not found at {path}. Run scripts/build_features.py first."
        )

    key = str(path.resolve())
    mtime = path.stat().st_mtime

    with _feature_table_cache_lock:
        cached = _feature_table_cache.get(key)
        if cached is not None and cached[0] == mtime:
            return cached[1]

    df = pd.read_parquet(path)

    with _feature_table_cache_lock:
        _feature_table_cache[key] = (mtime, df)
    return df


def get_user_feature_rows(user_id: str, features_path: Optional[Path] = None) -> pd.DataFrame:
    """Return unranked feature rows shared by leaderboard and recommendation generation."""
    df = load_feature_table(features_path)
    user_df = df[df["user_id"] == user_id]
    if user_df.empty:
        raise UnknownUserError(f"No content found for user_id {user_id}")
    return user_df


def build_leaderboard(user_id: str, features_path: Optional[Path] = None) -> dict:
    user_df = get_user_feature_rows(user_id, features_path)

    total_posts_in_history = len(user_df)

    ranked_mask = user_df["has_sufficient_group_history"]
    if "n_prior_in_group" in user_df.columns:  # Older feature tables may not include history depth.
        ranked_mask = ranked_mask & (user_df["n_prior_in_group"] >= MIN_PRIOR_POSTS_FOR_RANKING)
    ranked_df = user_df[ranked_mask].copy()
    ranked_df = ranked_df.sort_values("performance_z", ascending=False).reset_index(drop=True)
    ranked_df["rank"] = ranked_df.index + 1

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