import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timedelta, timezone
import pandas as pd
from app import insight_service as svc


def _row(user_id, content_id, days_ago, performance_z, content_type="carousel", hook_type="story",
         topic_tags=("transformation",), posting_hour=19, niche="fitness", has_history=True,
         performance_raw=0.05, platform="instagram"):
    return {
        "user_id": user_id, "content_id": content_id, "niche": niche, "platform": platform,
        "performance_raw": performance_raw,
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
    hooks = result["dimensions"]["hook_type"]
    assert hooks[0]["is_standout"] is True


def test_personal_patterns_has_no_content_type_dimension():
    # Each format has its own baseline, so these scores do not compare absolute format performance.
    df = pd.DataFrame([_row("u1", f"c{i}", 1, 1.5) for i in range(6)])
    assert "content_type" not in svc.personal_pattern_insights(df)["dimensions"]


def test_niche_top_patterns_never_reports_content_type():
    rows = [_row(f"u{i}", f"c{i}", 1, 1.0, content_type=ct) for i in range(20) for ct in ("carousel", "text")]
    result = svc.niche_top_patterns(pd.DataFrame(rows))
    assert result and all(r["dimension"] != "content_type" for r in result)


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


def _niche_frames(user_raw, other_raw, user_z=0.0, other_z=0.0, user_ct="carousel", other_ct="carousel"):
    user_rows = [_row("u1", f"c{i}", 1, user_z, performance_raw=user_raw, content_type=user_ct) for i in range(6)]
    other_rows = []
    for u in range(12):
        other_rows += [_row(f"other{u}", f"o{u}_{j}", 1, other_z, performance_raw=other_raw, content_type=other_ct)
                       for j in range(5)]
    return pd.DataFrame(user_rows), pd.DataFrame(user_rows + other_rows)


def test_niche_comparison_reports_engagement_ratio_against_same_format_posts():
    user_df, niche_df = _niche_frames(user_raw=0.10, other_raw=0.05)
    result = svc.niche_comparison(user_df, niche_df, "u1")
    assert result["sufficient_data"] is True
    assert result["user_median_engagement_rate"] == 0.1
    assert result["niche_median_engagement_rate"] == 0.05
    assert result["engagement_ratio"] == 2.0


def test_niche_comparison_ignores_performance_z_entirely():
    # Similar relative scores can coexist with very different absolute engagement rates.
    user_df, niche_df = _niche_frames(user_raw=0.50, other_raw=0.05, user_z=0.07, other_z=0.08)
    assert svc.niche_comparison(user_df, niche_df, "u1")["engagement_ratio"] == 10.0


def test_niche_comparison_only_compares_posts_of_the_same_platform_and_content_type():
    user_df, niche_df = _niche_frames(user_raw=0.10, other_raw=0.05, user_ct="text", other_ct="carousel")
    result = svc.niche_comparison(user_df, niche_df, "u1")
    assert result["sufficient_data"] is False  # no peer posts of the user's format to compare with


def test_niche_comparison_ranks_a_10x_creator_above_peers_using_real_expanding_z_scores():
    """Absolute engagement should rank a higher-performing creator above peers."""
    import numpy as np
    from features.builder import _compute_expanding_group_stats

    rng = np.random.default_rng(7)

    def user_frame(uid, level, n=60):
        raw = np.minimum((rng.pareto(3, n) + 1) * 0.02, 1.0) * level
        return pd.DataFrame({
            "user_id": uid, "platform": "instagram", "content_type": "carousel", "niche": "fitness",
            "content_id": [f"{uid}-{i}" for i in range(n)], "performance_raw": raw,
            "posted_at": [datetime.now(timezone.utc) - timedelta(days=n - i) for i in range(n)],
        })

    frames = [user_frame(f"peer{i}", 1.0) for i in range(12)] + [user_frame("star", 10.0)]
    scored = _compute_expanding_group_stats(pd.concat(frames, ignore_index=True))
    result = svc.niche_comparison(scored[scored["user_id"] == "star"], scored, "star")
    assert result["sufficient_data"] is True
    assert result["engagement_ratio"] > 5


def test_niche_top_patterns_requires_higher_min_n_than_personal():
    rows = [_row(f"u{i}", f"c{i}", 1, 1.0) for i in range(10)]  # 10 < NICHE_PATTERN_MIN_N (15)
    df = pd.DataFrame(rows)
    result = svc.niche_top_patterns(df)
    assert result == []