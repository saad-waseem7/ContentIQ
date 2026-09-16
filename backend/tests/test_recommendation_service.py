import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.recommendation_service import _compute_best_posting_time
from app.recommendation_service import _select_best_candidate


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
    winners_df = pd.DataFrame({"content_id": ["c1", "c2"]})  # no posting_hour/posting_day_of_week columns at all
    hour, weekday = _compute_best_posting_time(winners_df, fallback_hour=7, fallback_weekday=2)
    assert hour == 7
    assert weekday == 2    