import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import json as json_module
import uuid
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import leaderboard_service
from app.database import SessionLocal
from app import models as db_models
from app.main import app
from ml import idea_scoring

VALID_PAYLOAD = {
    "hook_type": "story", "content_type": "carousel", "platform": "instagram",
    "primary_topic_tag": "transformation", "duration_sec": None,
    "sample_caption": "Testing my own idea about a transformation story.",
}

class _StubClassifierForPredictTest:
        def predict_proba(self, X):
            return np.array([[0.3, 0.7]])


def _make_row(user_id, content_id, performance_z, label, has_history=True, niche="fitness"):
    return {
        "user_id": user_id, "content_id": content_id, "niche": niche, "platform": "instagram",
        "content_type": "carousel", "hook_type": "story", "topic_tags": ["transformation"],
        "posted_at": datetime.now(timezone.utc), "follower_count": 5000,
        "performance_raw": 0.05, "performance_z": performance_z,
        "label_overperformer": label, "has_sufficient_group_history": has_history,
    }


def _write_features(tmp_path, rows) -> Path:
    df = pd.DataFrame(rows)
    path = tmp_path / "features.parquet"
    df.to_parquet(path, index=False)
    return path


def test_predict_rejects_invalid_platform():
    client = TestClient(app)
    resp = client.post(f"/predict?user_id={uuid.uuid4()}", json=dict(VALID_PAYLOAD, platform="facebook"))
    assert resp.status_code == 422


def test_predict_404_when_user_has_no_winning_content(tmp_path, monkeypatch):
    user_id = str(uuid.uuid4())
    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=-1.0, label=False)]
    path = _write_features(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)

    client = TestClient(app)
    resp = client.post(f"/predict?user_id={user_id}", json=VALID_PAYLOAD)
    assert resp.status_code == 404


def test_predict_503_when_features_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", tmp_path / "nope.parquet")
    client = TestClient(app)
    resp = client.post(f"/predict?user_id={uuid.uuid4()}", json=VALID_PAYLOAD)
    assert resp.status_code == 503


def test_predict_503_when_model_artifacts_missing(tmp_path, monkeypatch):
    user_id = str(uuid.uuid4())
    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True)]
    path = _write_features(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "nope.joblib")

    client = TestClient(app)
    resp = client.post(f"/predict?user_id={user_id}", json=VALID_PAYLOAD)
    assert resp.status_code == 503


def test_predict_returns_score_for_valid_request(tmp_path, monkeypatch):
    user_id = str(uuid.uuid4())
    db = SessionLocal()
    db.add(db_models.User(id=uuid.UUID(user_id), niche="fitness", goal="test"))
    db.commit()
    db.close()

    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True) for _ in range(5)]
    path = _write_features(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)
    joblib.dump(_StubClassifierForPredictTest(), tmp_path / "classifier.joblib")

    (tmp_path / "category_levels.json").write_text(json_module.dumps({
        "content_type": ["carousel"], "hook_type": ["story"], "platform": ["instagram"],
        "niche": ["fitness"], "duration_bucket": ["not_applicable"], "follower_tier": ["5k_to_50k"],
        "primary_topic_tag": ["transformation"],
    }))
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "classifier.joblib")
    monkeypatch.setattr(idea_scoring, "CATEGORY_LEVELS_PATH", tmp_path / "category_levels.json")

    client = TestClient(app)
    resp = client.post(f"/predict?user_id={user_id}", json=VALID_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json()["predicted_score"] == pytest.approx(0.7)
    assert resp.json()["topic_recognized"] is True


def _setup_predict_artifacts(tmp_path, monkeypatch) -> str:
    user_id = str(uuid.uuid4())
    db = SessionLocal()
    db.add(db_models.User(id=uuid.UUID(user_id), niche="fitness", goal="test"))
    db.commit()
    db.close()

    rows = [_make_row(user_id, str(uuid.uuid4()), performance_z=2.0, label=True) for _ in range(5)]
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", _write_features(tmp_path, rows))
    joblib.dump(_StubClassifierForPredictTest(), tmp_path / "classifier.joblib")
    (tmp_path / "category_levels.json").write_text(json_module.dumps({
        "content_type": ["carousel"], "hook_type": ["story"], "platform": ["instagram"],
        "niche": ["fitness"], "duration_bucket": ["not_applicable"], "follower_tier": ["5k_to_50k"],
        "primary_topic_tag": ["transformation", "quick_recipes"],
    }))
    monkeypatch.setattr(idea_scoring, "MODEL_PATH", tmp_path / "classifier.joblib")
    monkeypatch.setattr(idea_scoring, "CATEGORY_LEVELS_PATH", tmp_path / "category_levels.json")
    return user_id


@pytest.mark.parametrize("typed", ["Transformation", "Quick Recipes", "quick recipes"])
def test_predict_recognizes_a_topic_typed_the_way_the_ui_displays_it(tmp_path, monkeypatch, typed):
    user_id = _setup_predict_artifacts(tmp_path, monkeypatch)
    resp = TestClient(app).post(f"/predict?user_id={user_id}", json=dict(VALID_PAYLOAD, primary_topic_tag=typed))
    assert resp.status_code == 200
    assert resp.json()["topic_recognized"] is True


def test_predict_flags_a_topic_the_model_has_never_seen(tmp_path, monkeypatch):
    user_id = _setup_predict_artifacts(tmp_path, monkeypatch)
    resp = TestClient(app).post(f"/predict?user_id={user_id}", json=dict(VALID_PAYLOAD, primary_topic_tag="gardening"))
    assert resp.status_code == 200
    assert resp.json()["topic_recognized"] is False