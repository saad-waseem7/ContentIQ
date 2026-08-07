import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timedelta, timezone

import pandas as pd

from ml import config as cfg
from ml.data_prep import prepare_model_matrix, temporal_train_test_split


def _make_row(user_id, days_offset, **overrides):
    base = {
        "content_id": uuid.uuid4(), "user_id": user_id, "niche": "fitness",
        "platform": "instagram", "content_type": "carousel", "hook_type": "story",
        "duration_bucket": "not_applicable", "follower_tier": "under_5k",
        "duration_sec": None, "caption_length_chars": 50, "caption_length_words": 10,
        "hashtag_count": 2, "emoji_count": 1, "has_cta": False, "posting_hour": 10,
        "posting_day_of_week": 1, "is_weekend": False, "sentiment_score": 0.0,
        "follower_count": 1000, "days_since_last_post": 1.0, "is_first_post_for_user": False,
        "content_type_share_recent": 0.5, "similarity_to_prior_winners": 0.1,
        "topic_tags": ["transformation"],
        "posted_at": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=days_offset),
        "performance_z": 0.0, "label_overperformer": False,
    }
    base.update(overrides)
    return base

def test_split_keeps_test_rows_strictly_later_than_train_rows_per_user():
    user_id = uuid.uuid4()
    df = pd.DataFrame([_make_row(user_id, i) for i in range(10)])

    train, test = temporal_train_test_split(df)

    assert train[train["user_id"] == user_id]["posted_at"].max() < test[test["user_id"] == user_id]["posted_at"].min()


def test_prepare_model_matrix_excludes_leakage_columns():
    df = pd.DataFrame([_make_row(uuid.uuid4(), 0)])
    X = prepare_model_matrix(df)
    for leaked_col in cfg.LEAKAGE_EXCLUDED_COLUMNS:
        assert leaked_col not in X.columns