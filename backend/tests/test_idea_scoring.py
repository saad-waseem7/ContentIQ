import sys
from pathlib import Path
import joblib
from ml import idea_scoring

sys.path.append(str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone
import pytest

from ml import config as ml_cfg
from ml.idea_scoring import (
    ModelArtifactsNotFoundError,
    apply_known_category_levels,
    build_idea_feature_row,
    load_category_levels,
    load_classifier,
    score_idea,
)

IDEA = {
    "hook_type": "story",
    "content_type": "carousel",
    "platform": "instagram",
    "primary_topic_tag": "transformation",
    "duration_sec": None,
    "best_posting_window": "Tuesday 7-9pm",
    "sample_caption": "Here's the plan that changed everything.",
    "rationale": "Beat your median by 2x.",
}

USER_CONTEXT = {
    "niche": "fitness",
    "follower_count": 5000,
    "days_since_last_post": 3.0,
    "content_type_share_recent": 0.4,
    "is_first_post_for_user": False,
    "similarity_to_prior_winners": 0.6,
    "planned_posted_at": datetime(2026, 1, 1, 19, 0, tzinfo=timezone.utc),
}

class _DummyClassifierForCacheTest:
    def predict_proba(self, X):
        return [[0.5, 0.5]]

def test_feature_row_has_all_required_columns():
    df = build_idea_feature_row(IDEA, USER_CONTEXT)
    expected_before_prepare = [
        c for c in ml_cfg.CATEGORICAL_FEATURES if c != "primary_topic_tag"
    ] + ml_cfg.NUMERIC_FEATURES
    for col in expected_before_prepare:
        assert col in df.columns, f"missing column: {col}"
    assert "topic_tags" in df.columns
    assert df.shape[0] == 1


def test_none_duration_sec_becomes_numeric_nan_not_object_dtype():
    df = build_idea_feature_row(IDEA, USER_CONTEXT)
    assert df["duration_sec"].dtype.kind in ("f", "i")


def test_apply_known_category_levels_handles_unseen_value_as_nan():
    df = build_idea_feature_row(IDEA, USER_CONTEXT)
    fake_levels = {"content_type": ["short_video", "long_video"]}
    result = apply_known_category_levels(df, fake_levels)
    assert result["content_type"].isna().all()


def test_score_idea_raises_when_artifacts_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("ml.idea_scoring.MODEL_PATH", tmp_path / "nope.joblib")
    with pytest.raises(ModelArtifactsNotFoundError):
        load_classifier()
    monkeypatch.setattr("ml.idea_scoring.CATEGORY_LEVELS_PATH", tmp_path / "nope.json")
    with pytest.raises(ModelArtifactsNotFoundError):
        load_category_levels()


def test_build_idea_feature_row_uses_best_posting_time_when_present():
    ctx = dict(USER_CONTEXT)
    ctx["best_posting_hour"] = 20
    ctx["best_posting_weekday"] = 3  # Thursday
    df = build_idea_feature_row(IDEA, ctx)
    assert df["posting_hour"].iloc[0] == 20
    assert df["posting_day_of_week"].iloc[0] == 3
    assert df["is_weekend"].iloc[0] == 0


def test_build_idea_feature_row_falls_back_to_planned_posted_at_without_best_time():
    ctx = dict(USER_CONTEXT)  # no best_posting_hour/weekday keys
    df = build_idea_feature_row(IDEA, ctx)
    assert df["posting_hour"].iloc[0] == USER_CONTEXT["planned_posted_at"].hour
    assert (df["posting_day_of_week"].iloc[0] == USER_CONTEXT["planned_posted_at"].weekday())


def test_build_idea_feature_row_is_weekend_derived_from_best_weekday():
    ctx = dict(USER_CONTEXT)
    ctx["best_posting_hour"] = 10
    ctx["best_posting_weekday"] = 6  # Sunday
    df = build_idea_feature_row(IDEA, ctx)
    assert df["is_weekend"].iloc[0] == 1


def test_load_classifier_uses_cache_on_second_call(tmp_path, monkeypatch):
    idea_scoring.clear_artifact_cache()

    joblib.dump(_DummyClassifierForCacheTest(), tmp_path / "classifier.joblib")
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "classifier.joblib")

    m1 = idea_scoring.load_classifier()
    m2 = idea_scoring.load_classifier()
    assert m1 is m2