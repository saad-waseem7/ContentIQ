import json
import threading
import time
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd

import features.config as feat_cfg
import features.content_features as cf
from ml import config as ml_cfg
from ml.data_prep import prepare_model_matrix

MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "classifier.joblib"
CATEGORY_LEVELS_PATH = Path(__file__).resolve().parents[1] / "data" / "category_levels.json"


class ModelArtifactsNotFoundError(Exception):
    """classifier.joblib / category_levels.json missing — run scripts/train_model.py."""


# mtime-keyed in-memory cache — same rationale as leaderboard_service's
# feature table cache. A recommendation call scores 3 candidates; without
# this, that's 3 separate joblib.load() calls (deserializing the whole
# LightGBM booster) per single Generate click. classifier.joblib only
# changes when scripts/train_model.py reruns.
#
# Thread safety: LightGBM's Booster.predict/predict_proba is read-only
# inference against an already-fitted model — no mutation happens after
# load, so concurrent reads from multiple FastAPI threadpool threads are
# expected to be safe. This is standard practice for serving a cached model,
# but has not been independently stress-tested under heavy concurrent load
# in this project — flagging as an assumption, not a proven guarantee.
_classifier_cache: dict[str, tuple[float, object]] = {}
_category_levels_cache: dict[str, tuple[float, dict]] = {}
_artifact_cache_lock = threading.Lock()


def clear_artifact_cache() -> None:
    """Test/dev utility."""
    with _artifact_cache_lock:
        _classifier_cache.clear()
        _category_levels_cache.clear()


def load_classifier():
    if not MODEL_PATH.exists():
        raise ModelArtifactsNotFoundError(f"Classifier not found at {MODEL_PATH}. Run scripts/train_model.py first.")

    key = str(MODEL_PATH.resolve())
    mtime = MODEL_PATH.stat().st_mtime
    with _artifact_cache_lock:
        cached = _classifier_cache.get(key)
        if cached is not None and cached[0] == mtime:
            return cached[1]

    start = time.perf_counter()
    model = joblib.load(MODEL_PATH)
    print(f"[load_classifier] CACHE MISS — loaded from disk in {time.perf_counter() - start:.4f}s")

    with _artifact_cache_lock:
        _classifier_cache[key] = (mtime, model)
    return model


def load_category_levels() -> dict:
    if not CATEGORY_LEVELS_PATH.exists():
        raise ModelArtifactsNotFoundError(f"Category levels not found at {CATEGORY_LEVELS_PATH}. Run scripts/train_model.py first.")

    key = str(CATEGORY_LEVELS_PATH.resolve())
    mtime = CATEGORY_LEVELS_PATH.stat().st_mtime
    with _artifact_cache_lock:
        cached = _category_levels_cache.get(key)
        if cached is not None and cached[0] == mtime:
            return cached[1]

    levels = json.loads(CATEGORY_LEVELS_PATH.read_text())
    with _artifact_cache_lock:
        _category_levels_cache[key] = (mtime, levels)
    return levels


def _follower_tier(follower_count: Optional[float]) -> str:
    if follower_count is None or pd.isna(follower_count):
        return "unknown"
    return pd.cut([follower_count], bins=feat_cfg.FOLLOWER_BUCKETS, labels=feat_cfg.FOLLOWER_BUCKET_LABELS, right=False)[0]


def build_idea_feature_row(idea: dict, user_context: dict) -> pd.DataFrame:
    posted_at = user_context["planned_posted_at"]
    caption = idea["sample_caption"]

    best_hour = user_context.get("best_posting_hour")
    best_weekday = user_context.get("best_posting_weekday")
    posting_hour = best_hour if best_hour is not None else cf.posting_hour(posted_at)
    posting_day_of_week = best_weekday if best_weekday is not None else cf.posting_day_of_week(posted_at)
    is_weekend = posting_day_of_week >= 5

    row = {
        "content_type": idea["content_type"],
        "hook_type": idea["hook_type"],
        "platform": idea["platform"],
        "niche": user_context["niche"],
        "duration_bucket": cf.duration_bucket(idea.get("duration_sec")),
        "follower_tier": _follower_tier(user_context.get("follower_count")),
        "topic_tags": [idea["primary_topic_tag"]],
        "duration_sec": idea.get("duration_sec"),
        "caption_length_chars": cf.caption_length_chars(caption),
        "caption_length_words": cf.caption_length_words(caption),
        "hashtag_count": 0,
        "emoji_count": cf.emoji_count(caption),
        "has_cta": cf.has_cta(caption),
        "posting_hour": posting_hour,
        "posting_day_of_week": posting_day_of_week,
        "is_weekend": is_weekend,
        "sentiment_score": cf.sentiment_score(caption),
        "follower_count": user_context.get("follower_count"),
        "days_since_last_post": user_context.get("days_since_last_post"),
        "is_first_post_for_user": user_context.get("is_first_post_for_user", False),
        "content_type_share_recent": user_context.get("content_type_share_recent"),
        "similarity_to_prior_winners": user_context.get("similarity_to_prior_winners"),
    }
    df = pd.DataFrame([row])
    for col in ml_cfg.NUMERIC_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def apply_known_category_levels(X: pd.DataFrame, category_levels: dict) -> pd.DataFrame:
    X = X.copy()
    for col, levels in category_levels.items():
        if col in X.columns:
            X[col] = pd.Categorical(X[col], categories=levels)
    return X


def score_idea(idea: dict, user_context: dict) -> float:
    classifier = load_classifier()
    category_levels = load_category_levels()
    raw_df = build_idea_feature_row(idea, user_context)
    X = apply_known_category_levels(prepare_model_matrix(raw_df), category_levels)
    return float(classifier.predict_proba(X)[:, 1][0])