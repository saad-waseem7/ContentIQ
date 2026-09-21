import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timezone

import pandas as pd
import pytest
import time
from fastapi.testclient import TestClient

from app import leaderboard_service
from app.main import app


def _make_row(user_id, content_id, performance_z, has_history=True, niche="fitness", label=None):
    return {
        "user_id": user_id,
        "content_id": content_id,
        "niche": niche,
        "platform": "instagram",
        "content_type": "carousel",
        "hook_type": "story",
        "topic_tags": ["transformation"],
        "posted_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "performance_raw": 0.05,
        "performance_z": performance_z,
        "label_overperformer": label if label is not None else (performance_z is not None and performance_z > 0),
        "has_sufficient_group_history": has_history,
    }


def _write_parquet(tmp_path, rows) -> Path:
    df = pd.DataFrame(rows)
    path = tmp_path / "features.parquet"
    df.to_parquet(path, index=False)
    return path


def test_leaderboard_ordering_and_rank(tmp_path):
    user_id = str(uuid.uuid4())
    rows = [
        _make_row(user_id, "c1", performance_z=0.5),
        _make_row(user_id, "c2", performance_z=2.1),
        _make_row(user_id, "c3", performance_z=-0.8),
    ]
    path = _write_parquet(tmp_path, rows)

    result = leaderboard_service.build_leaderboard(user_id, features_path=path)

    zs = [entry["performance_z"] for entry in result["leaderboard"]]
    assert zs == sorted(zs, reverse=True)
    assert [entry["rank"] for entry in result["leaderboard"]] == [1, 2, 3]


def test_above_and_below_baseline_both_represented(tmp_path):
    user_id = str(uuid.uuid4())
    rows = [
        _make_row(user_id, "c1", performance_z=1.5, label=True),
        _make_row(user_id, "c2", performance_z=-1.2, label=False),
    ]
    path = _write_parquet(tmp_path, rows)

    result = leaderboard_service.build_leaderboard(user_id, features_path=path)

    top_flags = {entry["content_id"]: entry["is_top_performer"] for entry in result["leaderboard"]}
    assert top_flags["c1"] is True
    assert top_flags["c2"] is False


def test_insufficient_history_excluded_from_ranking_but_counted_in_total(tmp_path):
    user_id = str(uuid.uuid4())
    rows = [
        _make_row(user_id, "c1", performance_z=1.0, has_history=True),
        _make_row(user_id, "c2", performance_z=float("nan"), has_history=False),
        _make_row(user_id, "c3", performance_z=float("nan"), has_history=False),
    ]
    path = _write_parquet(tmp_path, rows)

    result = leaderboard_service.build_leaderboard(user_id, features_path=path)

    assert result["total_posts_in_history"] == 3
    assert result["ranked_posts"] == 1
    assert len(result["leaderboard"]) == 1
    assert result["leaderboard"][0]["content_id"] == "c1"


def test_multiple_users_filtered_correctly(tmp_path):
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    rows = [
        _make_row(user_a, "a1", performance_z=1.0),
        _make_row(user_b, "b1", performance_z=5.0),
    ]
    path = _write_parquet(tmp_path, rows)

    result = leaderboard_service.build_leaderboard(user_a, features_path=path)

    assert result["total_posts_in_history"] == 1
    assert all(entry["content_id"] == "a1" for entry in result["leaderboard"])


def test_unknown_user_raises(tmp_path):
    rows = [_make_row(str(uuid.uuid4()), "c1", performance_z=1.0)]
    path = _write_parquet(tmp_path, rows)

    with pytest.raises(leaderboard_service.UnknownUserError):
        leaderboard_service.build_leaderboard(str(uuid.uuid4()), features_path=path)


def test_missing_feature_file_raises(tmp_path):
    missing_path = tmp_path / "does_not_exist.parquet"
    with pytest.raises(leaderboard_service.FeatureDataNotBuiltError):
        leaderboard_service.build_leaderboard(str(uuid.uuid4()), features_path=missing_path)


def test_endpoint_returns_expected_shape(tmp_path, monkeypatch):
    user_id = str(uuid.uuid4())
    rows = [_make_row(user_id, "c1", performance_z=1.0)]
    path = _write_parquet(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)

    client = TestClient(app)
    resp = client.get(f"/content?user_id={user_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"user_id", "niche", "total_posts_in_history", "ranked_posts", "leaderboard"}
    assert body["leaderboard"][0]["content_id"] == "c1"


def test_endpoint_404_on_unknown_user(tmp_path, monkeypatch):
    rows = [_make_row(str(uuid.uuid4()), "c1", performance_z=1.0)]
    path = _write_parquet(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)

    client = TestClient(app)
    resp = client.get(f"/content?user_id={uuid.uuid4()}")
    assert resp.status_code == 404


def test_endpoint_503_when_feature_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", tmp_path / "nope.parquet")

    client = TestClient(app)
    resp = client.get(f"/content?user_id={uuid.uuid4()}")
    assert resp.status_code == 503


def test_load_feature_table_uses_cache_on_second_call(tmp_path, monkeypatch):
    leaderboard_service.clear_feature_table_cache()
    rows = [_make_row("u1", "c1", performance_z=1.0)]
    path = _write_parquet(tmp_path, rows)
    monkeypatch.setattr(leaderboard_service, "FEATURES_PATH", path)

    df1 = leaderboard_service.load_feature_table(path)
    df2 = leaderboard_service.load_feature_table(path)
    assert df1 is df2  # same object returned — proves the second call didn't re-read the file


def test_load_feature_table_reloads_after_file_changes(tmp_path, monkeypatch):
    leaderboard_service.clear_feature_table_cache()
    path = _write_parquet(tmp_path, [_make_row("u1", "c1", performance_z=1.0)])
    df1 = leaderboard_service.load_feature_table(path)

    time.sleep(0.01)
    path2 = _write_parquet(tmp_path, [_make_row("u1", "c1", performance_z=1.0), _make_row("u1", "c2", performance_z=2.0)])
    df2 = leaderboard_service.load_feature_table(path2)
    assert len(df2) == 2
    assert df1 is not df2