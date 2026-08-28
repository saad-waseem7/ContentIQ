import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

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