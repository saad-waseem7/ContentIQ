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


def test_metric_timezone_mismatch_is_a_validation_error_not_a_crash():
    from datetime import datetime, timezone

    import pytest
    from pydantic import ValidationError

    from app.schemas import ContentIngest

    base = {"channel_id": "00000000-0000-0000-0000-000000000000", "content_type": "image"}
    aware_post = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    naive_post = datetime(2026, 1, 5, 12, 0)

    # naive capture AFTER an aware post, and the reverse: valid, and no TypeError
    ContentIngest(**base, posted_at=aware_post, metrics=[{"captured_at": datetime(2026, 1, 6)}])
    ContentIngest(**base, posted_at=naive_post, metrics=[{"captured_at": datetime(2026, 1, 6, tzinfo=timezone.utc)}])

    # still rejected when the capture really is earlier, regardless of tz awareness
    with pytest.raises(ValidationError):
        ContentIngest(**base, posted_at=aware_post, metrics=[{"captured_at": datetime(2026, 1, 1)}])
    with pytest.raises(ValidationError):
        ContentIngest(**base, posted_at=naive_post, metrics=[{"captured_at": datetime(2026, 1, 1, tzinfo=timezone.utc)}])


def test_ingest_rejects_oversized_text_fields():
    uid = "00000000-0000-0000-0000-000000000001"
    assert client.post("/ingest", json={"user": {"niche": "n" * 201}}).status_code == 422
    assert client.post("/ingest", json={"user": {"niche": "fitness", "goal": "g" * 501}}).status_code == 422
    assert client.post(
        "/ingest", json={"channel": {"user_id": uid, "platform": "instagram", "handle": "h" * 201}}
    ).status_code == 422

    content = {"channel_id": uid, "content_type": "carousel", "posted_at": "2026-01-01T12:00:00Z"}
    assert client.post("/ingest", json={"content": dict(content, caption="c" * 5001)}).status_code == 422
    assert client.post("/ingest", json={"content": dict(content, title="t" * 301)}).status_code == 422
    assert client.post("/ingest", json={"content": dict(content, topic_tags=["a"] * 101)}).status_code == 422
    assert client.post("/ingest", json={"content": dict(content, hashtags=["h" * 201])}).status_code == 422


def _create_channel():
    user_id = client.post("/ingest", json={"user": {"niche": "fitness"}}).json()["user_id"]
    return client.post(
        "/ingest", json={"channel": {"user_id": user_id, "platform": "instagram", "handle": "dup_test"}}
    ).json()["channel_id"]


def test_ingest_duplicate_content_id_returns_409_and_keeps_the_original():
    channel_id = _create_channel()
    content = {
        "id": "7d0f3c1e-5b7a-4a43-9c5e-0d6f0f8f0a11",
        "channel_id": channel_id,
        "content_type": "carousel",
        "posted_at": "2026-01-01T12:00:00Z",
    }
    first = client.post("/ingest", json={"content": content})
    second = client.post("/ingest", json={"content": {**content, "title": "second attempt"}})

    assert first.status_code == 201
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


def test_ingest_rejects_negative_counts_and_durations():
    channel_id = _create_channel()
    base = {"channel_id": channel_id, "content_type": "short_video", "posted_at": "2026-01-01T12:00:00Z"}

    negative_duration = client.post("/ingest", json={"content": {**base, "duration_sec": -5}})
    negative_likes = client.post(
        "/ingest",
        json={"content": {**base, "metrics": [{"captured_at": "2026-01-02T12:00:00Z", "likes": -1}]}},
    )
    negative_followers = client.post(
        "/ingest", json={"channel": {"user_id": "7d0f3c1e-5b7a-4a43-9c5e-0d6f0f8f0a12", "platform": "x", "handle": "h", "follower_count": -1}}
    )

    assert negative_duration.status_code == 422
    assert negative_likes.status_code == 422
    assert negative_followers.status_code == 422


def test_ingest_still_allows_negative_followers_gained():
    channel_id = _create_channel()
    resp = client.post(
        "/ingest",
        json={"content": {
            "channel_id": channel_id, "content_type": "image", "posted_at": "2026-01-01T12:00:00Z",
            "metrics": [{"captured_at": "2026-01-02T12:00:00Z", "followers_gained": -3}],
        }},
    )
    assert resp.status_code == 201