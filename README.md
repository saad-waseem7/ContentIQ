# ContentIQ

ContentIQ is a personalized AI content coach for creators. It ingests posts and performance metrics, evaluates each post against the creator's own historical baseline, and generates content recommendations grounded in that creator's winning content.

This repository contains the MVP: a Dockerized FastAPI service, PostgreSQL with pgvector, a leakage-aware feature pipeline, LightGBM models, an LLM coaching layer, a Next.js frontend, and synthetic data tooling.

## Current capabilities

- Ingest users, channels, content, and time-series metrics through `POST /ingest`.
- Rank content by relative performance within the same user, platform, and content type.
- Generate caption embeddings with `all-MiniLM-L6-v2`.
- Build temporal features using only information available before each post.
- Train LightGBM classifier and regressor models with MLflow tracking and SHAP artifacts.
- Generate and persist recommendations using either a deterministic mock LLM or Gemini.
- Mark recommendations as `actioned` or `dismissed` from the frontend.
- Seed the database with multi-niche synthetic creator data.

## Architecture

```text
Next.js frontend
				|
				v
FastAPI REST API ---- PostgreSQL + pgvector
				|
				+---- feature and embedding pipeline
				+---- LightGBM classifier/regressor
				+---- MLflow tracking and artifacts
				+---- mock or Gemini coaching provider
```

## Technology

- **Frontend:** Next.js 14, React, TypeScript, Tailwind CSS
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Pydantic
- **Data:** PostgreSQL 16 with pgvector, Alembic
- **Machine learning:** LightGBM, scikit-learn, sentence-transformers, SHAP
- **Experiment tracking:** MLflow
- **Infrastructure:** Docker Compose

## Prerequisites

- Docker Desktop
- Git
- Python 3.11 or later for running the synthetic data generator locally
- Node.js 20 or later only if running the frontend outside Docker

## Quick start

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
```

The single Compose command starts PostgreSQL with pgvector, the FastAPI backend, MLflow, and the Next.js frontend. The API container does not run migrations automatically, so apply them whenever the database is new or the schema changes. No separate frontend or backend startup command is required.

Services:

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| FastAPI API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| MLflow | http://localhost:5001 |
| PostgreSQL | `localhost:${POSTGRES_PORT}` |

The default local database credentials and Docker-network URLs are in [.env.example](.env.example). Do not use those credentials outside local development.

## Seed synthetic data

The generator creates 45 users across fitness, food, and tech, with approximately 150-200 posts per user and three metric snapshots per post. It sends data to the running API at `http://localhost:8000/ingest`.

Run it from the repository root:

```powershell
python -m pip install -r synthetic_data/requirements.txt
python synthetic_data/generator.py
```

## Build and train the model

Run the pipeline in this order after seeding data:

```powershell
docker compose exec api python scripts/generate_embeddings.py
docker compose exec api python scripts/build_features.py
docker compose exec api python scripts/train_model.py
```

Generated artifacts include:

- `backend/data/features.parquet`
- `backend/data/classifier.joblib`
- `backend/data/category_levels.json`
- MLflow runs and artifacts in the configured tracking store

Optional commands:

```powershell
docker compose exec api python scripts/compute_baselines.py
docker compose exec api python scripts/verify_mlflow.py
docker compose exec api python scripts/train_model_pca_experiment.py
```

The PCA script is an experiment and does not replace the serving model.

### Feature and label behavior

Raw performance is calculated as:

```text
(likes + comments + shares + saves) / reach
```

Performance labels and user/context features are computed from strictly earlier posts in the same `(user, platform, content_type)` group. Posts without enough history are retained in the dataset but are excluded from leaderboard ranking and model labels where a prior baseline is unavailable.

## Environment variables

The root `.env` file supplies the backend and Docker services:

| Variable | Purpose |
| --- | --- |
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_DB` | PostgreSQL database name |
| `POSTGRES_PORT` | Host port mapped to PostgreSQL |
| `DATABASE_URL` | SQLAlchemy connection URL |
| `MLFLOW_TRACKING_URI` | MLflow tracking endpoint |
| `LLM_PROVIDER` | `mock` by default; use `gemini` for Gemini |
| `GEMINI_API_KEY` | Required when `LLM_PROVIDER=gemini` |
| `GEMINI_MODEL` | Gemini model name; defaults to `gemini-2.0-flash` |

The containerized frontend uses `http://localhost:8000` as its API URL by default. For a custom frontend deployment, set `NEXT_PUBLIC_API_BASE_URL` to the API URL. The frontend also accepts `NEXT_PUBLIC_DEFAULT_USER_ID` as an optional initial user ID.

The mock provider is deterministic and is the recommended default for local development and tests.

## API overview

Interactive request and response schemas are available at http://localhost:8000/docs.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check API and database connectivity |
| `POST` | `/ingest` | Create or update users, channels, content, and metrics |
| `GET` | `/content?user_id={uuid}` | Return a user's relative-performance leaderboard |
| `POST` | `/recommend?user_id={uuid}` | Generate and persist one recommendation |
| `POST` | `/recommendations/{id}/feedback` | Set recommendation status to `actioned` or `dismissed` |

Example health response:

```json
{"status":"ok","database":"connected"}
```

An ingest request may contain a user, channel, or content object. Parent records must already exist when referenced by `user_id` or `channel_id`; in practice, create them with separate requests. Content metrics must have a `captured_at` timestamp at or after `posted_at`.

The leaderboard and recommendation endpoints require the generated feature and model artifacts. Recommendations also require at least one prior winning post and a working LLM provider.

## Frontend

The root route redirects to `/leaderboard`. The frontend currently provides:

- A manually entered user UUID shared across screens.
- A relative-performance content leaderboard.
- Manual recommendation generation.
- Recommendation rationale, format, timing, predicted probability, and status.
- Action and dismiss feedback controls.
- Loading and error states.

The frontend is included in Docker Compose and is available at http://localhost:3000 after `docker compose up --build -d`. For containerized development, use the frontend service directly when needed:

```powershell
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

## Tests and CI

Run backend tests inside the API container:

```powershell
docker compose exec api pytest -v
```

Run frontend tests in the running frontend container:

```powershell
docker compose exec frontend npm test
```

Continuous integration runs backend migrations and tests against PostgreSQL with pgvector. The workflow is defined in [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Repository layout

```text
backend/
	app/                 FastAPI app, API routers, persistence, and services
	features/            Feature engineering, embeddings, and baselines
	llm/                 Coach provider abstraction, mock provider, and Gemini client
	ml/                  Modeling and evaluation modules
	scripts/             Embedding, feature, baseline, training, and MLflow commands
	migrations/          Alembic schema migrations
	tests/               Backend unit and integration tests
frontend/
	app/                 Next.js routes and page layouts
	components/          Shared UI components
	lib/                 API client and user context
synthetic_data/        Synthetic creator, content, and metric generator
docker-compose.yml     Local PostgreSQL, API, MLflow, and frontend services
```

## Scope and roadmap

The MVP intentionally does not yet include authentication, scheduled retraining or baseline refresh jobs, a production feedback-learning loop, insights endpoint, recommendation history, real social-platform connectors, OAuth, automatic ingestion, or CSV import. The live recommendation score is the classifier's predicted over-performer probability; the trained regressor is evaluated and logged but is not used for serving recommendations.

The intended next steps are to harden the evaluation gate, add scheduled jobs and structured insights, implement recommendation feedback learning, and connect one real platform behind a shared ingestion interface.