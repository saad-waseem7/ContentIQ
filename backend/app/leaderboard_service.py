import threading
import time
from pathlib import Path
from typing import Optional

import pandas as pd

FEATURES_PATH = Path(__file__).resolve().parents[1] / "data" / "features.parquet"


class FeatureDataNotBuiltError(Exception):
    """features.parquet doesn't exist yet — run scripts/build_features.py."""


class UnknownUserError(Exception):
    """user_id has no rows in the feature table."""


# In-memory cache, keyed by resolved file path, invalidated by mtime — not a
# TTL. features.parquet only changes when scripts/build_features.py is
# rerun, which changes its mtime; any other time it's read, the file is
# byte-identical, so re-parsing it is pure waste. Keying by path (not a
# single global variable) means tests that monkeypatch FEATURES_PATH to a
# unique tmp_path per test get their own cache entry, never colliding with
# the real data or with each other. Lock guards concurrent FastAPI
# threadpool requests from racing on the dict.
_feature_table_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_feature_table_cache_lock = threading.Lock()


def clear_feature_table_cache() -> None:
    """Clear cached feature tables so tests can verify a cold load."""
    with _feature_table_cache_lock:
        _feature_table_cache.clear()


def load_feature_table(features_path: Optional[Path] = None) -> pd.DataFrame:
    # Resolved at call time, not bind time — required so tests can monkeypatch
    # FEATURES_PATH and have it actually take effect on the next call.
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

    start = time.perf_counter()
    df = pd.read_parquet(path)
    elapsed = time.perf_counter() - start
    print(f"[load_feature_table] CACHE MISS — read {len(df)} rows from disk in {elapsed:.4f}s")

    with _feature_table_cache_lock:
        _feature_table_cache[key] = (mtime, df)
    return df


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

    ranked_df = user_df[user_df["has_sufficient_group_history"]].copy()
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