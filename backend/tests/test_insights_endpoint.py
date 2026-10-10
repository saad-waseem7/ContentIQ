import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timezone

import pandas as pd
from fastapi.testclient import TestClient

from app import insight_clustering, leaderboard_service
from app.main import app


def _make_row(user_id, content_id, performance_z, has_history=True, niche="fitness"):
    return {
        "user_id": user_id, "content_id": content_id, "niche": niche, "platform": "instagram",
        "content_type": "carousel", "hook_type": "story", "topic_tags": ["transformation"],
        "posting_hour": 19, "posted_at": datetime.now(timezone.utc),
        "has_sufficient_group_history": has_history, "performance_z": performance_z,
        "follower_count": 5000,
    }


def _write_features(tmp_path, rows) -> Path:
    df = pd.DataFrame(rows)
    path = tmp_path / "features.parquet"
    df.to_parquet(path, index=False)
    return path


def test_404_unknown_user(tmp_path, monkeypatch):
    path = _write_features(tmp_path, [_make_row(str(uuid.uuid4()), "c1", 1.0)])
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)
    client = TestClient(app)
    resp = client.get(f"/insights?user_id={uuid.uuid4()}")
    assert resp.status_code == 404


def test_503_when_features_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", tmp_path / "nope.parquet")
    client = TestClient(app)
    resp = client.get(f"/insights?user_id={uuid.uuid4()}")
    assert resp.status_code == 503


def test_200_response_shape_with_clustering_stubbed(tmp_path, monkeypatch):
    user_id = str(uuid.uuid4())
    rows = [_make_row(user_id, f"c{i}", 1.0) for i in range(6)]
    path = _write_features(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)

    # Keep this endpoint test independent of the database embedding query.
    monkeypatch.setattr(
        insight_clustering, "load_and_compute_niche_clusters",
        lambda db, niche, df: ({"available": False, "reason_unavailable": "stubbed for test"}, None)
    )

    client = TestClient(app)
    resp = client.get(f"/insights?user_id={user_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["niche"] == "fitness"
    assert "personal_patterns" in body
    assert "trend" in body
    assert "niche_comparison" in body
    assert body["topic_clusters"]["available"] is False