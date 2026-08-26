import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timezone

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import leaderboard_service
from app.main import app
from ml import idea_scoring


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
    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True)]
    path = _write_features(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "nope.joblib")

    client = TestClient(app)
    resp = client.post(f"/recommend?user_id={user_id}")
    assert resp.status_code == 503


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