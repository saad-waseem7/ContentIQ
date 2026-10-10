import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.recommendation_service import _compute_best_posting_time
from app.recommendation_service import _select_best_candidate
from app import recommendation_service as rs


def test_select_best_candidate_picks_highest_score_not_first():
    candidates = [({"id": "a"}, 0.2), ({"id": "b"}, 0.9), ({"id": "c"}, 0.5)]
    idea, score = _select_best_candidate(candidates)
    assert idea == {"id": "b"}
    assert score == 0.9


def test_select_best_candidate_single_candidate():
    candidates = [({"id": "only"}, 0.4)]
    idea, score = _select_best_candidate(candidates)
    assert idea == {"id": "only"}
    assert score == 0.4


def test_compute_best_posting_time_returns_mode_of_winners():
    winners_df = pd.DataFrame({
        "posting_hour": [19, 19, 19, 8, 20],
        "posting_day_of_week": [1, 1, 3, 1, 1],
    })
    hour, weekday = _compute_best_posting_time(winners_df, fallback_hour=0, fallback_weekday=0)
    assert hour == 19
    assert weekday == 1


def test_compute_best_posting_time_deterministic_tie_break_picks_lowest():
    winners_df = pd.DataFrame({"posting_hour": [9, 20], "posting_day_of_week": [2, 4]})
    hour, weekday = _compute_best_posting_time(winners_df, fallback_hour=99, fallback_weekday=99)
    assert hour == 9
    assert weekday == 2


def test_compute_best_posting_time_falls_back_on_missing_data():
    winners_df = pd.DataFrame({"posting_hour": [None, None], "posting_day_of_week": [None, None]})
    hour, weekday = _compute_best_posting_time(winners_df, fallback_hour=12, fallback_weekday=3)
    assert hour == 12
    assert weekday == 3


def test_compute_best_posting_time_falls_back_on_empty_dataframe():
    winners_df = pd.DataFrame({"posting_hour": [], "posting_day_of_week": []})
    hour, weekday = _compute_best_posting_time(winners_df, fallback_hour=5, fallback_weekday=1)
    assert hour == 5
    assert weekday == 1    


def test_compute_best_posting_time_falls_back_when_columns_entirely_absent():
    winners_df = pd.DataFrame({"content_id": ["c1", "c2"]})  # Exercise tables without posting-time features.
    hour, weekday = _compute_best_posting_time(winners_df, fallback_hour=7, fallback_weekday=2)
    assert hour == 7
    assert weekday == 2


def _winners(rows):
    return pd.DataFrame(rows, columns=["performance_z", "n_prior_in_group"])


def test_grounding_prefers_posts_with_a_stable_baseline_over_higher_z_early_posts():
    winners = _winners([(9.0, 3), (8.0, 4), (7.0, 5)] + [(1.0 + i * 0.1, 40) for i in range(5)])
    top = rs._select_grounding_posts(winners)
    assert len(top) == rs.GROUNDING_TOP_K
    assert (top["n_prior_in_group"] == 40).all()


def test_grounding_fills_remaining_slots_with_early_posts_when_too_few_stable_ones_exist():
    winners = _winners([(1.5, 40), (1.2, 40), (9.0, 3), (8.0, 4), (7.0, 5), (6.0, 6)])
    top = rs._select_grounding_posts(winners)
    assert list(top["performance_z"]) == [1.5, 1.2, 9.0, 8.0, 7.0]


def test_grounding_falls_back_to_plain_z_order_for_feature_tables_without_history_depth():
    winners = pd.DataFrame({"performance_z": [0.5, 2.0, 1.0]})
    assert list(rs._select_grounding_posts(winners)["performance_z"]) == [2.0, 1.0, 0.5]


def test_creator_profile_uses_the_dominant_platform_its_formats_and_topics_by_frequency():
    df = pd.DataFrame({
        "platform": ["instagram"] * 5 + ["x"] * 2,
        "content_type": ["carousel", "carousel", "carousel", "image", "image", "text", "text"],
        "topic_tags": [["a"], ["a"], ["b"], ["b"], ["a"], ["c"], None],
    })
    profile = rs._build_creator_profile(df)
    assert profile["platform"] == "instagram"
    assert profile["content_types"] == ["carousel", "image"]  # formats used on that platform only
    assert profile["topics"] == ["a", "b", "c"]


def test_base_context_uses_the_creators_median_hashtag_count(monkeypatch):
    monkeypatch.setattr(rs, "_get_content_embeddings", lambda db, ids: {})
    import uuid
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    ids = [str(uuid.uuid4()) for _ in range(3)]
    user_df = pd.DataFrame({
        "content_id": ids, "niche": "fitness", "follower_count": 1000, "hashtag_count": [1, 2, 9],
        "posted_at": [now - timedelta(days=d) for d in (3, 2, 1)], "content_type": "image",
    })
    ctx = rs._build_base_user_context(None, user_df, user_df)
    assert ctx["hashtag_count"] == 2.0


def test_base_context_tolerates_feature_tables_without_hashtag_count(monkeypatch):
    monkeypatch.setattr(rs, "_get_content_embeddings", lambda db, ids: {})
    import uuid
    from datetime import datetime, timezone

    user_df = pd.DataFrame({
        "content_id": [str(uuid.uuid4())], "niche": "fitness", "follower_count": 1000,
        "posted_at": [datetime.now(timezone.utc)], "content_type": "image",
    })
    assert rs._build_base_user_context(None, user_df, user_df)["hashtag_count"] is None

