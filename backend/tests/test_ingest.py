import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ingest_full_flow_user_channel_content():
    user_resp = client.post("/ingest", json={"user": {"niche": "fitness", "goal": "grow followers"}})
    assert user_resp.status_code == 201
    user_id = user_resp.json()["user_id"]
    assert user_id is not None

    channel_resp = client.post(
        "/ingest",
        json={"channel": {"user_id": user_id, "platform": "instagram", "handle": "test_handle", "follower_count": 1000}},
    )
    assert channel_resp.status_code == 201
    channel_id = channel_resp.json()["channel_id"]
    assert channel_id is not None

    content_resp = client.post(
        "/ingest",
        json={
            "content": {
                "channel_id": channel_id,
                "content_type": "carousel",
                "hook_type": "story",
                "topic_tags": ["transformation"],
                "posted_at": "2026-01-01T12:00:00Z",
                "metrics": [
                    {"captured_at": "2026-01-02T12:00:00Z", "impressions": 1000, "reach": 800, "likes": 50, "comments": 5, "shares": 2, "saves": 10}
                ],
            }
        },
    )
    assert content_resp.status_code == 201
    body = content_resp.json()
    assert body["content_id"] is not None
    assert body["metrics_created"] == 1


def test_ingest_rejects_invalid_platform():
    resp = client.post(
        "/ingest",
        json={"channel": {"user_id": "00000000-0000-0000-0000-000000000000", "platform": "facebook", "handle": "x"}},
    )
    assert resp.status_code == 422


def test_ingest_rejects_unknown_channel_id():
    resp = client.post(
        "/ingest",
        json={
            "content": {
                "channel_id": "00000000-0000-0000-0000-000000000000",
                "content_type": "image",
                "posted_at": "2026-01-01T12:00:00Z",
            }
        },
    )
    assert resp.status_code == 422


def test_ingest_rejects_metric_before_posted_at():
    resp = client.post(
        "/ingest",
        json={
            "content": {
                "channel_id": "00000000-0000-0000-0000-000000000000",
                "content_type": "image",
                "posted_at": "2026-01-05T12:00:00Z",
                "metrics": [{"captured_at": "2026-01-01T12:00:00Z", "likes": 1}],
            }
        },
    )
    assert resp.status_code == 422