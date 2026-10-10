import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timezone

import pandas as pd
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import leaderboard_service
from app.main import app
from llm.mock_client import MockLLMClient
from ml import idea_scoring


class _StubClassifierAscendingScores:
    """Returns increasing scores on successive calls — proves the endpoint
    actually picks the LAST-scored (highest) candidate, not just the first
    one generated, which would silently pass a weaker test."""
    call_count = 0

    def predict_proba(self, X):
        _StubClassifierAscendingScores.call_count += 1
        score = 0.2 * _StubClassifierAscendingScores.call_count
        return np.array([[1 - score, score]])


class _ThreeDistinctIdeasClient:
    """Maps each strategy directive to a fixed caption.

    Candidates are generated in parallel threads, so the order in which calls arrive is not
    deterministic. Keying on the directive in the prompt keeps candidate i paired with
    caption i regardless of thread scheduling."""

    def __init__(self):
        self.captions = [
            "First candidate idea about transformation.",
            "Second candidate idea, a different angle entirely.",
            "Third candidate idea, yet another take.",
        ]

    def generate(self, prompt: str) -> str:
        import json
        from llm.coach import STRATEGY_DIRECTIVES
        index = next(i for i, directive in enumerate(STRATEGY_DIRECTIVES) if directive in prompt)
        return json.dumps({
            "hook_type": "story", "content_type": "carousel", "platform": "instagram",
            "primary_topic_tag": "transformation", "duration_sec": None,
            "best_posting_window": "Tuesday 7-9pm", "sample_caption": self.captions[index],
            "rationale": "Beat your median by 2x based on real data.",
        })


def _install_stub_model(tmp_path, monkeypatch):
    """Writes minimal model artifacts. /recommend checks they exist before it calls the LLM."""
    import json as json_module
    import joblib

    joblib.dump(_StubClassifierAscendingScores(), tmp_path / "classifier.joblib")
    (tmp_path / "category_levels.json").write_text(json_module.dumps({
        "content_type": ["carousel"], "hook_type": ["story"], "platform": ["instagram"],
        "niche": ["fitness"], "duration_bucket": ["not_applicable"], "follower_tier": ["5k_to_50k"],
        "primary_topic_tag": ["transformation"],
    }))
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "classifier.joblib")
    monkeypatch.setattr(idea_scoring, "CATEGORY_LEVELS_PATH", tmp_path / "category_levels.json")


def test_recommend_selects_highest_scored_candidate_not_first(tmp_path, monkeypatch):
    import json as json_module
    import joblib
    from app.database import SessionLocal
    from app import models as db_models

    user_id = str(uuid.uuid4())
    db = SessionLocal()
    db.add(db_models.User(id=uuid.UUID(user_id), niche="fitness", goal="test"))
    db.commit()
    db.close()

    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True) for _ in range(5)]
    path = _write_features(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)

    _StubClassifierAscendingScores.call_count = 0
    joblib.dump(_StubClassifierAscendingScores(), tmp_path / "classifier.joblib")
    (tmp_path / "category_levels.json").write_text(json_module.dumps({
        "content_type": ["carousel"], "hook_type": ["story"], "platform": ["instagram"],
        "niche": ["fitness"], "duration_bucket": ["not_applicable"], "follower_tier": ["5k_to_50k"],
        "primary_topic_tag": ["transformation"],
    }))
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "classifier.joblib")
    monkeypatch.setattr(idea_scoring, "CATEGORY_LEVELS_PATH", tmp_path / "category_levels.json")

    import app.routers.recommend as recommend_router
    monkeypatch.setattr(recommend_router, "_llm_client", _ThreeDistinctIdeasClient())

    client = TestClient(app)
    resp = client.post(f"/recommend?user_id={user_id}")

    assert resp.status_code == 201
    body = resp.json()
    assert "Third candidate idea" in body["idea_text"]
    assert body["predicted_score"] == pytest.approx(0.6)

    
def _make_row(user_id, content_id, performance_z, label, has_history=True, niche="fitness"):
    return {
        "user_id": user_id,
        "content_id": content_id,
        "niche": niche,
        "platform": "instagram",
        "content_type": "carousel",
        "hook_type": "story",
        "topic_tags": ["transformation"],
        "posted_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "follower_count": 5000,
        "performance_raw": 0.05,
        "performance_z": performance_z,
        "label_overperformer": label,
        "has_sufficient_group_history": has_history,
    }


def _write_features(tmp_path, rows) -> Path:
    df = pd.DataFrame(rows)
    path = tmp_path / "features.parquet"
    df.to_parquet(path, index=False)
    return path


def _create_db_user(user_id: str) -> None:
    from app.database import SessionLocal
    from app import models as db_models

    db = SessionLocal()
    try:
        db.add(db_models.User(id=uuid.UUID(user_id), niche="fitness", goal="test"))
        db.commit()
    finally:
        db.close()


class _CountingClient:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return "{}"


def test_404_when_user_has_no_winning_content(tmp_path, monkeypatch):
    user_id = str(uuid.uuid4())
    rows = [_make_row(user_id, "c1", performance_z=-1.0, label=False)]
    path = _write_features(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)

    client = TestClient(app)
    resp = client.post(f"/recommend?user_id={user_id}")
    assert resp.status_code == 404


def test_503_when_features_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", tmp_path / "nope.parquet")
    client = TestClient(app)
    resp = client.post(f"/recommend?user_id={uuid.uuid4()}")
    assert resp.status_code == 503


def test_503_when_model_artifacts_missing(tmp_path, monkeypatch):
    from llm.mock_client import MockLLMClient
    import app.routers.recommend as recommend_router
    monkeypatch.setattr(recommend_router, "_llm_client", MockLLMClient())

    user_id = str(uuid.uuid4())
    _create_db_user(user_id)
    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True)]
    path = _write_features(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "nope.joblib")

    client = TestClient(app)
    resp = client.post(f"/recommend?user_id={user_id}")
    assert resp.status_code == 503


def test_502_when_llm_provider_fails_or_times_out(tmp_path, monkeypatch):
    from llm.base import LLMGenerationError

    class _TimingOutClient:
        def __init__(self):
            self.calls = 0

        def generate(self, prompt: str) -> str:
            self.calls += 1
            raise LLMGenerationError("Gemini API call failed or was blocked: 504 Deadline Exceeded")

    user_id = str(uuid.uuid4())
    _create_db_user(user_id)
    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True) for _ in range(5)]
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", _write_features(tmp_path, rows))
    _install_stub_model(tmp_path, monkeypatch)

    import app.routers.recommend as recommend_router
    client_stub = _TimingOutClient()
    monkeypatch.setattr(recommend_router, "_llm_client", client_stub)

    resp = TestClient(app).post(f"/recommend?user_id={user_id}")

    assert resp.status_code == 502
    assert "Deadline Exceeded" in resp.json()["detail"]
    assert client_stub.calls == 6  # 3 candidates x MAX_ATTEMPTS, then a clean failure


def test_recommend_rejects_oversized_user_id():
    resp = TestClient(app).post(f"/recommend?user_id={'u' * 65}")
    assert resp.status_code == 422


def test_404_without_calling_llm_when_user_missing_from_db(tmp_path, monkeypatch):
    import app.routers.recommend as recommend_router
    llm = _CountingClient()
    monkeypatch.setattr(recommend_router, "_llm_client", llm)

    user_id = str(uuid.uuid4())  # present in the feature table, deliberately absent from Postgres
    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True)]
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", _write_features(tmp_path, rows))

    client = TestClient(app)
    resp = client.post(f"/recommend?user_id={user_id}")

    assert resp.status_code == 404
    assert llm.calls == 0


def test_feedback_updates_status(tmp_path, monkeypatch):
    client = TestClient(app)
    fake_id = str(uuid.uuid4())
    resp = client.post(f"/recommendations/{fake_id}/feedback", json={"status": "actioned"})
    assert resp.status_code == 404


def test_feedback_rejects_invalid_status():
    client = TestClient(app)
    resp = client.post(f"/recommendations/{uuid.uuid4()}/feedback", json={"status": "not_a_real_status"})
    assert resp.status_code == 422


def test_feedback_404_on_unknown_recommendation_id():
    client = TestClient(app)
    resp = client.post(f"/recommendations/{uuid.uuid4()}/feedback", json={"status": "dismissed"})
    assert resp.status_code == 404


def test_feedback_404_on_malformed_recommendation_id():
    client = TestClient(app)
    resp = client.post("/recommendations/not-a-uuid/feedback", json={"status": "dismissed"})
    assert resp.status_code == 404


class _PlatformRecordingClassifier:
    seen_platforms: list = []

    def predict_proba(self, X):
        _PlatformRecordingClassifier.seen_platforms.append(X["platform"].iloc[0])
        return np.array([[0.5, 0.5]])


class _PromptRecordingMock(MockLLMClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return super().generate(prompt)


def test_recommend_scores_with_the_creators_platform_and_tells_the_llm_about_it(tmp_path, monkeypatch):
    import json as json_module
    import joblib
    import app.routers.recommend as recommend_router

    user_id = str(uuid.uuid4())
    _create_db_user(user_id)
    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True) for _ in range(5)]  # instagram
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", _write_features(tmp_path, rows))

    _PlatformRecordingClassifier.seen_platforms = []
    joblib.dump(_PlatformRecordingClassifier(), tmp_path / "classifier.joblib")
    (tmp_path / "category_levels.json").write_text(json_module.dumps({
        "content_type": ["carousel"], "hook_type": ["story"], "platform": ["instagram", "tiktok"],
        "niche": ["fitness"], "duration_bucket": ["not_applicable"], "follower_tier": ["5k_to_50k"],
        "primary_topic_tag": ["transformation"],
    }))
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "classifier.joblib")
    monkeypatch.setattr(idea_scoring, "CATEGORY_LEVELS_PATH", tmp_path / "category_levels.json")

    llm = _PromptRecordingMock(response_overrides={"platform": "tiktok"})  # the LLM ignores the instruction
    monkeypatch.setattr(recommend_router, "_llm_client", llm)

    resp = TestClient(app).post(f"/recommend?user_id={user_id}")

    assert resp.status_code == 201
    assert all("publishes on instagram" in p for p in llm.prompts)
    assert len(_PlatformRecordingClassifier.seen_platforms) == 3
    assert set(_PlatformRecordingClassifier.seen_platforms) == {"instagram"}  # never the LLM's tiktok



def test_503_for_missing_model_is_raised_before_any_llm_call(tmp_path, monkeypatch):
    import app.routers.recommend as recommend_router
    llm = _CountingClient()
    monkeypatch.setattr(recommend_router, "_llm_client", llm)

    user_id = str(uuid.uuid4())
    _create_db_user(user_id)
    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True)]
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", _write_features(tmp_path, rows))
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "nope.joblib")

    resp = TestClient(app).post(f"/recommend?user_id={user_id}")

    assert resp.status_code == 503
    assert llm.calls == 0