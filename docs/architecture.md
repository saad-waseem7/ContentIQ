# Architecture

This document describes how ContentIQ is put together and where its state lives. For the maths behind labels and features see [ml-pipeline.md](ml-pipeline.md). For the recommendation flow see [recommendations.md](recommendations.md).

## Components

```text
                     +---------------------------+
 synthetic_data/     |  FastAPI (backend/app)    |        +-----------------+
 generator.py  ----->|  routers -> services      |<------>| PostgreSQL 16   |
   POST /ingest      |                           |        | + pgvector      |
                     |  reads  backend/data/*    |        +-----------------+
 Next.js frontend -->|  writes recommendations   |
   JSON over HTTP    |  calls LLM (recommend)    |------> Gemini API or mock client
                     +---------------------------+
                                ^
                                | files written by hand-run scripts
                     +---------------------------+        +-----------------+
                     | backend/scripts           |------->| MLflow server   |
                     | embeddings, features, ML  |        | (train_model)   |
                     +---------------------------+        +-----------------+
```

| Component | Location | Responsibility |
| --- | --- | --- |
| API | `backend/app` | HTTP routes, request validation, services for leaderboard, insights and recommendations. |
| Feature pipeline | `backend/features` | Performance metric, leakage-safe labels, content features, embeddings, topic normalization. |
| ML | `backend/ml` | Training data preparation, LightGBM models, evaluation, SHAP, inference-time scoring, atomic file writes. |
| LLM layer | `backend/llm` | Provider-neutral client interface, prompt construction, output validation, Gemini and mock clients. |
| Batch scripts | `backend/scripts` | Entry points that build embeddings, baselines, the feature table and the model. |
| Data generator | `synthetic_data` | Creates creators, channels, posts and metric snapshots and posts them to `/ingest`. |
| Frontend | `frontend` | Four pages (Leaderboard, Daily Recommendation, Insights, History) plus the Try Your Own Idea panel on the recommendation page. The root path redirects to the leaderboard. All pages are client components. |

The classifier is the only model used at serving time. A LightGBM regressor is trained and tracked in MLflow, but nothing in the API uses it.

## Docker topology

`docker-compose.yml` defines four services.

| Service | Image or build | Host port | Notes |
| --- | --- | --- | --- |
| `db` | `pgvector/pgvector:pg16` | `${POSTGRES_PORT}` to 5432 | Data in the `pgdata` volume. Health-checked with `pg_isready`. |
| `api` | `backend/Dockerfile` (Python 3.11) | 8000 | Starts after `db` is healthy. Runs `uvicorn --reload`. `./backend` is bind-mounted at `/app`. |
| `mlflow` | `ghcr.io/mlflow/mlflow:v2.19.0` | 5001 to 5000 | SQLite store and artifacts in the `mlflow_data` volume. |
| `frontend` | `frontend/Dockerfile` (Node 20) | 3000 | Runs `npm run dev`. `./frontend` is bind-mounted, with anonymous volumes over `node_modules` and `.next`. |

Because `./backend` is bind-mounted, the files in `backend/data/` live on your host, not in a Docker volume. They survive `docker compose down -v`; the database does not. See [setup.md](setup.md#resetting-state).

`backend/.dockerignore` and `frontend/.dockerignore` keep `.env` files, virtual environments, `node_modules`, `.next`, caches and `backend/data` out of the image build context. Compose still passes the root `.env` to the containers at runtime, and the bind mounts expose your working tree to them.

## Where state lives

| State | Location | Written by | Read by |
| --- | --- | --- | --- |
| Users, channels, content, metric snapshots | PostgreSQL | `/ingest` | Embedding, baseline and feature scripts; the insights clustering step |
| Caption embeddings | PostgreSQL, `content.caption_embedding` | `generate_embeddings.py` | `build_features.py`, `/insights` clustering, `/recommend`, `/predict` |
| User baselines | PostgreSQL, `user_baselines` | `compute_baselines.py` | Nothing in the application |
| Recommendations | PostgreSQL, `recommendations` | `/recommend`, feedback endpoint | `/recommendations`, feedback endpoint |
| Feature table | `backend/data/features.parquet` | `build_features.py` | Leaderboard, insights, recommendations, prediction, `train_model.py` |
| Classifier | `backend/data/classifier.joblib` | `train_model.py` | Recommendations, prediction |
| Category levels | `backend/data/category_levels.json` | `train_model.py` | Recommendations, prediction |
| PCA experiment output | `backend/data/experiments/` | `train_model_pca_experiment.py` | Nothing in the application |
| Experiment runs, metrics, model copies | MLflow volume | `train_model.py` | MLflow UI |
| Theme choice | Browser `localStorage`, key `contentiq-theme` | Frontend | Frontend |

`backend/data/` is gitignored. A fresh clone has no feature table or model, and the API answers 503 until the pipeline has run.

The serving path reads the feature table, not the metrics tables. Data ingested after the last `build_features.py` run is invisible to the leaderboard, insights, recommendations and prediction. A new model does not exist until `train_model.py` runs again.

## Database schema

Three Alembic migrations in `backend/migrations/versions` build the schema. Run them with `alembic upgrade head`.

| Revision | Adds |
| --- | --- |
| `13e4d55222d0` | `CREATE EXTENSION vector`, then `users`, `channels`, `content`, `metrics` |
| `32a099c6fe86` | `user_baselines` |
| `421a0e038dd3` | `recommendations` |

| Table | Columns | Constraints |
| --- | --- | --- |
| `users` | `id` (UUID), `niche` (text), `goal` (text, nullable), `created_at` | Primary key |
| `channels` | `id`, `user_id`, `platform`, `handle`, `follower_count` (nullable) | FK to `users` (cascade); platform in the six allowed values |
| `content` | `id`, `channel_id`, `content_type`, `title`, `caption`, `hashtags` (text[]), `topic_tags` (text[]), `hook_type` (nullable), `duration_sec` (nullable), `posted_at`, `caption_embedding` (vector(384), nullable) | FK to `channels` (cascade); content type and hook type checked; indexes on `channel_id` and `posted_at` |
| `metrics` | `id`, `content_id`, `captured_at`, `impressions`, `reach`, `views`, `likes`, `comments`, `shares`, `saves`, `watch_time_sec`, `avg_pct_watched`, `followers_gained` | FK to `content` (cascade); indexes on `content_id` and `captured_at` |
| `user_baselines` | `user_id`, `platform`, `content_type` (composite key), `rolling_median_perf`, `p25`, `p75`, `updated_at` | FK to `users` (cascade); platform and content type checked |
| `recommendations` | `id`, `user_id`, `idea_text`, `format`, `best_time`, `rationale`, `predicted_score`, `status`, `linked_content_id` (nullable), `created_at` | FK to `users` (cascade) and `content` (set null); `format` in the content types; `status` in `proposed`, `actioned`, `dismissed` |

Closed value lists:

- Platforms: `youtube`, `youtube_shorts`, `instagram`, `tiktok`, `x`, `linkedin`
- Content types: `short_video`, `long_video`, `image`, `carousel`, `text`
- Hook types: `question`, `bold_claim`, `listicle`, `story`, `none`

The lists live in `backend/app/models.py` and are baked into the CHECK constraints as literals. Changing a list needs a new migration as well as a code change. `niche` is free text. The model knows only the niches it was trained on.

`recommendations.linked_content_id` exists in the schema but no code sets it.

## pgvector: what is and is not used

pgvector is used as a storage type and nothing else.

- The first migration enables the extension, and `content.caption_embedding` is a `vector(384)` column matching the output size of `all-MiniLM-L6-v2`.
- `generate_embeddings.py` encodes `title + caption`, normalises each vector to unit length and writes it to that column.
- Application code reads the vectors back into NumPy. Cosine similarity (the `similarity_to_prior_winners` feature) and KMeans clustering (topic clusters) are computed in Python.
- There are no vector indexes, no distance operators in any SQL, and no similarity search over the database. Recommendation grounding ranks posts by `performance_z`, not by vector retrieval.

Retrieval by vector similarity was considered and deferred, because ranking by performance already met the functional need.

## Request flows

**Leaderboard (`GET /content`).** Load the feature table through the file-mtime cache, filter to the user, keep rows with enough prior history, sort by `performance_z`, return.

**Insights (`GET /insights`).** Same table, then aggregate in pandas. The only database use is loading caption embeddings for the niche's topic clusters, behind a per-niche cache.

**Recommendation (`POST /recommend`).** Load the user's rows, pick winning posts, build a creator profile, ask the LLM for three candidates in parallel, validate each, embed the captions, score each with the classifier, persist the best one. See [recommendations.md](recommendations.md).

**Custom idea score (`POST /predict`).** Same context building and scoring as above, with the idea supplied by the caller. No LLM call and nothing saved.

**Feedback and history.** Plain reads and updates on `recommendations`.

## Caching

| Cache | Scope | Key | Invalidation |
| --- | --- | --- | --- |
| Feature table | API process | Resolved file path | File modification time |
| Classifier and category levels | API process | Resolved file path | File modification time |
| Niche topic clusters | API process | Niche | Count of embedded posts in the niche plus a fingerprint of the niche's valid feature rows |
| Frontend GET responses | Browser tab | Full URL | 30 second TTL, plus explicit invalidation after generating a recommendation or submitting feedback |

All server caches are per process. The compose setup runs one uvicorn process, so they behave as a single cache. With several workers each would hold its own copy and warm up independently.

Artifact files are written atomically (write to a `.tmp` sibling, then `os.replace`), so a request never reads a half-written file. `train_model.py` writes `category_levels.json` before `classifier.joblib`. A request that lands between the two writes pairs the old model with the new levels, which is safe when a retrain adds categories.

## Design decisions worth knowing

- **One global model with per-user features.** There is no model per creator. Per-creator behavior enters through the history-based label and features.
- **Relative performance.** Every post is judged against the same creator's earlier posts on the same platform and format. A post can rank high on the leaderboard with a low absolute engagement rate.
- **LLM behind an interface.** `LLMClient.generate(prompt) -> str` is the whole contract. `get_llm_client()` is called once when the recommendation router is imported, so changing provider settings needs an API restart.
- **Mock by default.** The mock client returns fixed JSON, which keeps tests and local runs free and deterministic.
- **Insights are deterministic.** No LLM is involved in the Insights screen.
