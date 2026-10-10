import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timedelta, timezone
import pandas as pd
from features.builder import compute_feature_table


def _make_post(user_id, platform, content_type, days_offset, likes, comments, shares, saves, reach):
    return {
        "content_id": uuid.uuid4(),
        "user_id": user_id,
        "niche": "fitness",
        "platform": platform,
        "content_type": content_type,
        "follower_count": 10000,
        "title": "test post",
        "caption": "a normal caption",
        "hashtags": ["#test"],
        "hook_type": "story",
        "duration_sec": None,
        "posted_at": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=days_offset),
        "captured_at": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=days_offset + 1),
        "likes": likes, "comments": comments, "shares": shares, "saves": saves, "reach": reach,
    }


def _build_scenario(last_post_likes: int) -> pd.DataFrame:
    user_id = uuid.uuid4()
    rows = [
        _make_post(user_id, "instagram", "carousel", 0, 50, 5, 2, 10, 1000),
        _make_post(user_id, "instagram", "carousel", 1, 60, 6, 2, 12, 1000),
        _make_post(user_id, "instagram", "carousel", 2, 55, 5, 3, 11, 1000),
        _make_post(user_id, "instagram", "carousel", 3, 70, 7, 3, 14, 1000),
        _make_post(user_id, "instagram", "carousel", 4, last_post_likes, 5, 2, 10, 1000),
    ]
    return pd.DataFrame(rows)


def test_early_post_features_unaffected_by_future_post_metrics():
    """Changing the last post's metrics must not change earlier posts' z-scores or labels."""
    baseline_df = _build_scenario(last_post_likes=52)
    viral_df = _build_scenario(last_post_likes=50000)

    baseline_features = compute_feature_table(baseline_df, embeddings={}).sort_values("posted_at").reset_index(drop=True)
    viral_features = compute_feature_table(viral_df, embeddings={}).sort_values("posted_at").reset_index(drop=True)

    pd.testing.assert_series_equal(
        baseline_features.loc[:3, "performance_z"], viral_features.loc[:3, "performance_z"], check_names=False
    )
    pd.testing.assert_series_equal(
        baseline_features.loc[:3, "label_overperformer"], viral_features.loc[:3, "label_overperformer"], check_names=False
    )


def test_first_posts_in_group_have_no_label_insufficient_history():
    """The first post has no label because it has no prior group history."""
    df = _build_scenario(last_post_likes=52)
    features = compute_feature_table(df, embeddings={}).sort_values("posted_at").reset_index(drop=True)

    assert features.loc[0, "has_sufficient_group_history"] == False
    assert pd.isna(features.loc[0, "performance_z"])


def test_days_since_last_post_uses_only_prior_post():
    df = _build_scenario(last_post_likes=52)
    features = compute_feature_table(df, embeddings={}).sort_values("posted_at").reset_index(drop=True)

    assert pd.isna(features.loc[0, "days_since_last_post"])
    assert features.loc[1, "days_since_last_post"] == 1.0


def test_n_prior_in_group_counts_only_strictly_earlier_posts_in_the_same_group():
    df = _build_scenario(last_post_likes=52)
    features = compute_feature_table(df, embeddings={}).sort_values("posted_at").reset_index(drop=True)
    assert list(features["n_prior_in_group"]) == [0, 1, 2, 3, 4]


def test_n_prior_in_group_is_independent_across_groups():
    user_id = uuid.uuid4()
    rows = [_make_post(user_id, "instagram", "carousel", d, 50, 5, 2, 10, 1000) for d in range(3)]
    rows += [_make_post(user_id, "instagram", "image", d + 10, 50, 5, 2, 10, 1000) for d in range(2)]
    features = compute_feature_table(pd.DataFrame(rows), embeddings={})
    by_type = {ct: sorted(g["n_prior_in_group"]) for ct, g in features.groupby("content_type")}
    assert by_type == {"carousel": [0, 1, 2], "image": [0, 1]}

