import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app


def _create_user(db, niche="fitness"):
    user = models.User(id=uuid.uuid4(), niche=niche, goal="test")
    db.add(user)
    db.commit()
    return user.id


def _create_recommendation(db, user_id, created_at, status="proposed", score=0.5, text="idea"):
    rec = models.Recommendation(
        id=uuid.uuid4(), user_id=user_id, idea_text=text, format="carousel",
        best_time="Tuesday 7-9pm", rationale="test rationale citing 1 number",
        predicted_score=score, status=status,
    )
    db.add(rec)
    db.commit()
    db.execute(
        models.Recommendation.__table__.update()
        .where(models.Recommendation.id == rec.id)
        .values(created_at=created_at)
    )
    db.commit()
    return rec.id


def test_returns_correct_users_recommendations_newest_first():
    db = SessionLocal()
    try:
        user_id = _create_user(db)
        now = datetime.now(timezone.utc)
        id_old = _create_recommendation(db, user_id, now - timedelta(days=2), text="older idea")
        id_new = _create_recommendation(db, user_id, now, text="newer idea")
    finally:
        db.close()

    client = TestClient(app)
    resp = client.get(f"/recommendations?user_id={user_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert [r["id"] for r in body["recommendations"]] == [str(id_new), str(id_old)]


def test_empty_history_for_existing_user():
    db = SessionLocal()
    try:
        user_id = _create_user(db)
    finally:
        db.close()

    client = TestClient(app)
    resp = client.get(f"/recommendations?user_id={user_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["recommendations"] == []


def test_404_for_nonexistent_user():
    client = TestClient(app)
    resp = client.get(f"/recommendations?user_id={uuid.uuid4()}")
    assert resp.status_code == 404


def test_404_for_malformed_user_id():
    client = TestClient(app)
    resp = client.get("/recommendations?user_id=not-a-uuid")
    assert resp.status_code == 404


def test_no_cross_user_data_leakage():
    db = SessionLocal()
    try:
        user_a = _create_user(db)
        user_b = _create_user(db)
        now = datetime.now(timezone.utc)
        _create_recommendation(db, user_a, now, text="user a idea")
        _create_recommendation(db, user_b, now, text="user b idea")
    finally:
        db.close()

    client = TestClient(app)
    resp = client.get(f"/recommendations?user_id={user_a}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["recommendations"][0]["idea_text"] == "user a idea"