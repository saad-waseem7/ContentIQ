"""
Feature-izes a generated idea + a user's real current context into the exact
vector the Week 4 classifier expects, then scores it. Reuses
features/content_features.py, features/embeddings.py, and
ml/data_prep.py::prepare_model_matrix directly — no feature logic duplicated.
"""
import json
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


def load_classifier():
    if not MODEL_PATH.exists():
        raise ModelArtifactsNotFoundError(f"Classifier not found at {MODEL_PATH}. Run scripts/train_model.py first.")
    return joblib.load(MODEL_PATH)


def load_category_levels() -> dict:
    if not CATEGORY_LEVELS_PATH.exists():
        raise ModelArtifactsNotFoundError(f"Category levels not found at {CATEGORY_LEVELS_PATH}. Run scripts/train_model.py first.")
    return json.loads(CATEGORY_LEVELS_PATH.read_text())


def _follower_tier(follower_count: Optional[float]) -> str:
    if follower_count is None or pd.isna(follower_count):
        return "unknown"
    return pd.cut([follower_count], bins=feat_cfg.FOLLOWER_BUCKETS, labels=feat_cfg.FOLLOWER_BUCKET_LABELS, right=False)[0]


def build_idea_feature_row(idea: dict, user_context: dict) -> pd.DataFrame:
    posted_at = user_context["planned_posted_at"]
    caption = idea["sample_caption"]
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
        "hashtag_count": 0,  # LLM output has no separate hashtags field for MVP
        "emoji_count": cf.emoji_count(caption),
        "has_cta": cf.has_cta(caption),
        "posting_hour": cf.posting_hour(posted_at),
        "posting_day_of_week": cf.posting_day_of_week(posted_at),
        "is_weekend": cf.is_weekend(posted_at),
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
    """Re-casts categorical columns to the levels fitted at TRAINING time, not
    levels inferred from this single row — LightGBM requires identical
    category sets between train and predict. A value not seen in training
    becomes NaN, handled as missing, not a crash."""
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