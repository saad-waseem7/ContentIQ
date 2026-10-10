# API reference

The API is a FastAPI application (`backend/app/main.py`). It listens on port 8000 and serves interactive documentation at `/docs` and the OpenAPI schema at `/openapi.json`. Everything below was checked against the router code and, for status codes and response shapes, against a running instance with a small generated dataset and the mock LLM.

## Conventions

- **No authentication.** Every `user_id` and recommendation ID is caller-supplied and nothing checks who is asking. See [limitations.md](limitations.md#security-considerations).
- **CORS.** Only the origin `http://localhost:3000` is allowed, for `GET` and `POST`, with the `Content-Type` header. The list is hard-coded in `main.py`.
- **IDs.** Creator IDs and recommendation IDs are UUID strings, but most endpoints take them as plain strings. A malformed ID is treated as "not found" and returns 404, not 422.
- **Errors come in two shapes.**
  - Application errors: `{"detail": "message"}`.
  - Request validation errors (HTTP 422): `{"detail": [{"type": "...", "loc": ["body", "platform"], "msg": "...", "input": ..., "ctx": ...}]}`.
  - An unhandled exception returns HTTP 500 with the plain text `Internal Server Error`.
- **No pagination, rate limiting or versioning.**
- **Timestamps** are ISO 8601. Send timezone-aware values.
- **The feature table is a snapshot.** `/content`, `/insights`, `/recommend` and `/predict` read `backend/data/features.parquet` and, for the last two, `classifier.joblib`. Data ingested after the last pipeline run is not reflected. See [setup.md](setup.md#pipeline-reference).

## Summary

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/health` | Liveness and database check | 200 |
| POST | `/ingest` | Create users, channels, content and metric snapshots | 201 |
| GET | `/content` | Leaderboard for one creator | 200 |
| GET | `/insights` | Insights for one creator | 200 |
| POST | `/recommend` | Generate, score and save a recommendation | 201 |
| GET | `/recommendations` | Saved recommendations for one creator | 200 |
| POST | `/recommendations/{recommendation_id}/feedback` | Mark a recommendation actioned or dismissed | 200 |
| POST | `/predict` | Score a user-supplied idea | 200 |

## Input limits

Applied by Pydantic at the API boundary and returned as 422 when exceeded.

| Field | Limit |
| --- | --- |
| `user.niche`, `channel.handle` | 200 characters |
| `user.goal` | 500 characters |
| `content.title` | 300 characters |
| `content.caption`, `/predict` `sample_caption` | 5,000 characters |
| `/predict` `primary_topic_tag` | 200 characters |
| `content.hashtags`, `content.topic_tags` | 100 items, 200 characters each |
| `user_id` query parameter on `/predict`, `/recommend`, `/recommendations` | 64 characters |
| `recommendation_id` path parameter | 64 characters |

`duration_sec`, `follower_count` and the metric counts (`impressions`, `reach`, `views`, `likes`, `comments`, `shares`, `saves`, `watch_time_sec`, `avg_pct_watched`) must be zero or greater, otherwise 422. `followers_gained` may be negative. There are no upper bounds.

## GET /health

Runs `SELECT 1`.

```json
{"status": "ok", "database": "connected"}
```

An unreachable database returns 503 with `{"detail": "Database is not reachable"}`.

## POST /ingest

Creates records. The body must contain at least one of `user`, `channel`, `content`; they are processed in that order in a single transaction. A `ValueError` (for example an unknown channel) rolls everything back and returns 422.

```json
{
  "user":    {"id": "optional uuid", "niche": "fitness", "goal": "grow followers"},
  "channel": {"id": "optional uuid", "user_id": "uuid", "platform": "instagram",
              "handle": "my_handle", "follower_count": 12000},
  "content": {"id": "optional uuid", "channel_id": "uuid", "content_type": "carousel",
              "title": "...", "caption": "...", "hashtags": ["#a"], "topic_tags": ["transformation"],
              "hook_type": "story", "duration_sec": null, "posted_at": "2026-01-01T12:00:00Z",
              "metrics": [{"captured_at": "2026-01-02T12:00:00Z", "impressions": 1000, "reach": 800,
                           "views": null, "likes": 50, "comments": 5, "shares": 2, "saves": 10,
                           "watch_time_sec": null, "avg_pct_watched": null, "followers_gained": 3}]}
}
```

Response, 201. Fields for parts that were not in the request are `null`:

```json
{"user_id": "uuid", "channel_id": null, "content_id": null, "metrics_created": 0}
```

Validation:

| Field | Rule |
| --- | --- |
| `channel.platform` | One of the six platforms |
| `content.content_type` | One of the five content types |
| `content.hook_type` | One of the five hook types, or null |
| `content.metrics[].captured_at` | Must not be earlier than `content.posted_at` |
| `channel.user_id`, `content.channel_id` | Must reference an existing record, otherwise 422 with `... does not exist` |
| `content.id` | If supplied, must not already exist, otherwise 409 |
| `user.niche` | Free text, not validated against a list |

Behavior to be aware of:

- **Existing records are never updated.** If `user.id` or `channel.id` already exists, the existing row is returned unchanged and the other submitted fields are ignored. The endpoint is create or return, not upsert.
- **Content always inserts.** Posting a `content.id` that already exists returns 409 (`content <id> already exists`) and nothing from that request is saved. Content is never updated.
- Ingesting data does not change any served result until the pipeline is rerun.

## GET /content

Query: `user_id` (required).

Returns the creator's posts ranked by `performance_z`, highest first. Only posts with at least 10 earlier posts in the same platform and content-type group are ranked. See [insights-and-leaderboard.md](insights-and-leaderboard.md#leaderboard).

```json
{
  "user_id": "uuid",
  "niche": "fitness",
  "total_posts_in_history": 78,
  "ranked_posts": 68,
  "leaderboard": [
    {"rank": 1, "content_id": "uuid", "platform": "youtube_shorts", "content_type": "short_video",
     "hook_type": "story", "topic_tags": ["transformation"], "posted_at": "2025-12-17T11:15:00Z",
     "performance_raw": 0.1637, "performance_z": 11.45, "is_top_performer": true}
  ]
}
```

`total_posts_in_history` counts the creator's rows in the feature table, which excludes posts without a usable reach value. `is_top_performer` is the over-performer label: the post beat the 75th percentile of the earlier posts in its group. The whole ranked list is returned in one response.

| Status | When |
| --- | --- |
| 404 | The user is not in the feature table |
| 422 | `user_id` missing |
| 503 | `features.parquet` does not exist (checked before the user lookup) |

## GET /insights

Query: `user_id` (required).

Returns all insight sections in one response. Field meanings and thresholds are in [insights-and-leaderboard.md](insights-and-leaderboard.md#insights). Values below are illustrative.

```json
{
  "user_id": "uuid",
  "niche": "fitness",
  "personal_patterns": {
    "total_posts_analyzed": 75,
    "dimensions": {
      "hook_type": [{"value": "story", "n": 12, "mean_performance_z": 0.874, "is_standout": true}],
      "topic": [],
      "posting_time_window": []
    }
  },
  "trend": {"sufficient_data": true, "recent_period_days": 60, "recent_mean_performance_z": -0.21,
            "recent_n": 21, "historical_mean_performance_z": 0.641, "historical_n": 54,
            "direction": "declining", "note": "Descriptive only ..."},
  "monthly_performance": [{"period": "2026-03", "mean_performance_z": 0.12, "n": 6}],
  "niche_comparison": {"sufficient_data": false, "user_n": 75, "niche_other_users_n": 3,
                       "niche_total_posts_n": 205, "user_median_engagement_rate": null,
                       "niche_median_engagement_rate": null, "engagement_ratio": null},
  "niche_top_patterns": [{"dimension": "hook_type", "value": "story", "n": 40,
                          "mean_performance_z": 0.55, "is_standout": true}],
  "topic_clusters": {"available": true, "reason_unavailable": null, "k": 4, "silhouette_score": 0.21,
                     "clusters": [], "user_cluster_summary": []}
}
```

`trend.direction` is `improving`, `declining`, `stable` or `insufficient_data`. When `topic_clusters.available` is false, `reason_unavailable` explains why.

| Status | When |
| --- | --- |
| 404 | The user is not in the feature table |
| 422 | `user_id` missing |
| 503 | `features.parquet` does not exist |

## POST /recommend

Query: `user_id` (required, at most 64 characters). No body.

Generates three candidates with the configured LLM, scores each with the classifier and saves the highest-scoring one. This is the only endpoint that calls the LLM, and a single request can make up to six Gemini calls. The flow is described in [recommendations.md](recommendations.md).

Response, 201:

```json
{
  "id": "uuid",
  "idea_text": "[carousel / story hook / transformation] Here's the exact 90-day plan that changed everything for me.",
  "format": "carousel",
  "best_time": "Tuesday 7-9pm",
  "rationale": "Your top matching post scored 11.45 standard deviations above your own baseline.",
  "predicted_score": 0.609,
  "status": "proposed",
  "created_at": "2026-10-10T02:36:54.469936Z"
}
```

- `idea_text` is `[content_type / hook_type hook / topic] caption`.
- `predicted_score` is the classifier's probability, from 0 to 1, that the idea would beat the 75th percentile of the creator's earlier posts. It is not a percentage of anything and has not been calibrated.
- `best_time` is free text written by the LLM, shown to the user and not used in scoring.
- `status` starts as `proposed`.

| Status | When |
| --- | --- |
| 404 | The user is not in the feature table, has no winning posts, or does not exist in PostgreSQL. A malformed ID also returns 404. |
| 422 | `user_id` missing or longer than 64 characters |
| 502 | The LLM failed or returned invalid output for all three candidates. Nothing is saved. |
| 503 | `features.parquet` or the model files are missing. Both are checked before any LLM call. |

## GET /recommendations

Query: `user_id` (required, at most 64 characters).

```json
{"user_id": "uuid", "count": 1, "recommendations": [ /* same objects as POST /recommend, newest first */ ]}
```

| Status | When |
| --- | --- |
| 404 | No user with this ID in PostgreSQL, including malformed IDs |
| 422 | `user_id` missing or too long |

A user with no recommendations returns `count: 0` and an empty list.

## POST /recommendations/{recommendation_id}/feedback

Body:

```json
{"status": "actioned"}
```

`status` must be `actioned` or `dismissed`. Any other value, including `proposed`, returns 422. The response is the updated recommendation object. The status can be changed again later in either direction. The endpoint does not check who owns the recommendation.

| Status | When |
| --- | --- |
| 404 | Unknown or malformed recommendation ID |
| 422 | Invalid `status`, or the path ID is longer than 64 characters |

## POST /predict

Query: `user_id` (required, at most 64 characters).

Scores an idea the caller supplies. It builds the creator's context exactly as `/recommend` does but makes no LLM call and saves nothing.

```json
{
  "hook_type": "story",
  "content_type": "short_video",
  "platform": "youtube_shorts",
  "primary_topic_tag": "Transformation",
  "duration_sec": 30,
  "sample_caption": "My 90 day plan"
}
```

| Field | Rule |
| --- | --- |
| `hook_type`, `content_type`, `platform` | Closed lists, as above |
| `primary_topic_tag` | Required, not blank, at most 200 characters |
| `sample_caption` | Required, not blank, at most 5,000 characters |
| `duration_sec` | Optional integer, zero or greater |

Response, 200:

```json
{"predicted_score": 0.91, "topic_recognized": true}
```

`topic_recognized` is `false` when the model was never trained on this topic after normalization (lowercasing, spaces and hyphens to underscores). The idea is still scored, with the topic treated as missing, so the topic has no influence on the result. The platform is taken as submitted and is not forced to the creator's own platform, unlike in `/recommend`.

| Status | When |
| --- | --- |
| 404 | The user is not in the feature table, has no winning posts, or the ID is malformed |
| 422 | Invalid enum value, blank caption or topic, oversized field, missing `user_id` |
| 503 | `features.parquet` or the model files are missing |

Unlike `/recommend`, this endpoint does not check that the user exists in PostgreSQL. The feature table alone is enough.
