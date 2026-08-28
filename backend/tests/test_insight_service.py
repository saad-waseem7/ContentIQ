import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timedelta, timezone

import pandas as pd

from app import insight_service as svc


def _row(user_id, content_id, days_ago, performance_z, content_type="carousel", hook_type="story",
         topic_tags=("transformation",), posting_hour=19, niche="fitness", has_history=True):
    return {
        "user_id": user_id, "content_id": content_id, "niche": niche, "platform": "instagram",
        "content_type": content_type, "hook_type": hook_type, "topic_tags": list(topic_tags),
        "posting_hour": posting_hour,
        "posted_at": datetime.now(timezone.utc) - timedelta(days=days_ago),
        "has_sufficient_group_history": has_history, "performance_z": performance_z,
    }


def test_dimension_breakdown_excludes_groups_below_min_n():
    df = pd.DataFrame([_row("u1", f"c{i}", 1, 1.0, content_type="carousel") for i in range(5)]
                       + [_row("u1", "c6", 1, 2.0, content_type="text")])  # only 1 text post
    df = svc._add_primary_topic(df)
    result = svc._dimension_breakdown(svc._valid_rows(df), "content_type", min_n=5)
    values = [r["value"] for r in result]
    assert "carousel" in values
    assert "text" not in values


def test_personal_patterns_marks_standout_correctly():
    rows = [_row("u1", f"c{i}", 1, 1.5) for i in range(6)]  # mean well above 0.5
    df = pd.DataFrame(rows)
    result = svc.personal_pattern_insights(df)
    ct = result["dimensions"]["content_type"]
    assert ct[0]["is_standout"] is True


def test_trend_insufficient_data_when_too_few_per_period():
    rows = [_row("u1", f"c{i}", 1, 1.0) for i in range(2)]  # only 2 recent, no historical
    df = pd.DataFrame(rows)
    result = svc.trend_insights(df)
    assert result["sufficient_data"] is False
    assert result["direction"] == "insufficient_data"
    assert "not why" in result["note"]


def test_trend_detects_improving_direction():
    recent = [_row("u1", f"r{i}", 5, 2.0) for i in range(6)]
    historical = [_row("u1", f"h{i}", 100, 0.0) for i in range(6)]
    df = pd.DataFrame(recent + historical)
    result = svc.trend_insights(df)
    assert result["sufficient_data"] is True
    assert result["direction"] == "improving"


def test_monthly_performance_excludes_low_count_months():
    rows = [_row("u1", "c1", 400, 1.0)]  # single post, its own month
    df = pd.DataFrame(rows)
    result = svc.monthly_performance(df)
    assert result == []  # n=1 < MONTHLY_MIN_N


def test_niche_comparison_insufficient_when_too_few_other_users():
    user_id = "u1"
    user_rows = [_row(user_id, f"c{i}", 1, 1.0) for i in range(5)]
    other_rows = [_row(f"other{i}", f"o{i}", 1, 0.5) for i in range(3)]  # only 3 other users
    niche_df = pd.DataFrame(user_rows + other_rows)
    user_df = pd.DataFrame(user_rows)
    result = svc.niche_comparison(user_df, niche_df, user_id)
    assert result["sufficient_data"] is False
    assert result["niche_other_users_n"] == 3


def test_niche_comparison_sufficient_computes_delta():
    user_id = "u1"
    user_rows = [_row(user_id, f"c{i}", 1, 2.0) for i in range(5)]
    other_rows = []
    for u in range(12):
        other_rows += [_row(f"other{u}", f"o{u}_{j}", 1, 0.0) for j in range(5)]
    niche_df = pd.DataFrame(user_rows + other_rows)
    user_df = pd.DataFrame(user_rows)
    result = svc.niche_comparison(user_df, niche_df, user_id)
    assert result["sufficient_data"] is True
    assert result["delta"] == round(2.0 - 0.0, 3)


def test_niche_top_patterns_requires_higher_min_n_than_personal():
    rows = [_row(f"u{i}", f"c{i}", 1, 1.0) for i in range(10)]  # 10 < NICHE_PATTERN_MIN_N (15)
    df = pd.DataFrame(rows)
    result = svc.niche_top_patterns(df)
    assert result == []