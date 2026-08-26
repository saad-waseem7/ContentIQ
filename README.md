# ContentIQ

**ContentIQ is a personalized AI content coach for creators.** It learns what works for an individual creator, rather than applying generic best practices. Each post is evaluated against that creator's own historical baseline, then the resulting model and an LLM are used to generate grounded, scored content ideas.

This repository contains the MVP: a Dockerized FastAPI service, PostgreSQL with pgvector, a leakage-aware feature pipeline, LightGBM models, an LLM coaching layer, a Next.js frontend, and synthetic data tooling.

The complete development stack runs through one Docker Compose command. Migrations, synthetic data generation, and model preparation remain explicit commands because they are data and release-pipeline operations rather than service startup tasks.

## Current capabilities

- Ingest users, channels, content, and time-series metrics through `POST /ingest`.
- Rank content by relative performance within the same user, platform, and content type.
- Generate caption embeddings with `all-MiniLM-L6-v2`.
- Build temporal features using only information available before each post.
- Train LightGBM classifier and regressor models with MLflow tracking and SHAP artifacts.
- Generate and persist recommendations using either a deterministic mock LLM or Gemini.
- Mark recommendations as `actioned` or `dismissed` from the frontend.
- Seed the database with multi-niche synthetic creator data.

## Why ContentIQ

Generic advice such as "post at 7pm" or "use carousels" ignores that performance is relative to a creator's audience, niche, platform, and history. ContentIQ normalizes performance within each `(user, platform, content_type)` group and asks a more useful question: **what is likely to beat this creator's own baseline?**

Recommendations are grounded in the creator's highest-performing posts. The LLM receives the creator's niche and top content patterns, returns one structured idea, and must include a numeric rationale. The same trained model then converts the idea into the production feature space and scores its probability of being an over-performer.

## Architecture

```text
Next.js frontend
				|
				v
Synthetic data generator --POST /ingest--> FastAPI REST API ---- PostgreSQL + pgvector
				|
				+---- feature and embedding pipeline
				+---- LightGBM classifier/regressor
				+---- MLflow tracking and artifacts
				+---- mock or Gemini coaching provider
				|
				+---- idea -> feature vector -> model score
```

The Next.js frontend consumes the REST API for the leaderboard, recommendation generation, and feedback actions.

## Technology

- **Frontend:** Next.js 14, React, TypeScript, Tailwind CSS
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Pydantic
- **Data:** PostgreSQL 16 with pgvector, Alembic
- **Machine learning:** LightGBM, scikit-learn, sentence-transformers, SHAP
- **Experiment tracking:** MLflow
- **LLM:** Provider-agnostic interface with deterministic mock and Google Gemini implementations
- **Testing:** pytest, Vitest, React Testing Library
- **CI:** GitHub Actions
- **Infrastructure:** Docker Compose

## Engineering highlights

- **Leakage-safe features:** expanding-window features use only strictly prior posts, enforced by dedicated tests.
- **Planted-signal validation:** synthetic data contains niche-specific hook/topic effects, and SHAP analysis checks that the classifier recovers them.
- **Relative evaluation:** classifier performance is compared with a content-type-average baseline using a per-user temporal split.
- **Provider-agnostic LLM layer:** `LLMClient` isolates the recommendation pipeline from the provider. The mock client supports deterministic end-to-end tests; Gemini can be enabled without changing consuming code.
- **Structured LLM guardrails:** generated JSON is validated against the same platform, content-type, and hook-type values used by the backend. Invalid output is retried before the request fails, and rationales must contain a numeric citation.
- **Reproducible experiments:** MLflow records the data snapshot hash, model parameters, metrics, trained models, feature importance, and SHAP artifacts.
- **PCA experiment retained separately:** embedding reduction is available as an experiment and does not replace the shipped serving model.

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

Run it from the repository root. Python is needed locally for this data-generation command; the application services themselves run in Docker:

```powershell
python -m pip install -r synthetic_data/requirements.txt
python synthetic_data/generator.py
```

## Build and train the model

Run the pipeline in this order after seeding data:

```powershell
docker compose exec api python scripts/compute_baselines.py
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

`train_model.py` performs a temporal per-user split, trains both a classifier and regressor, saves the classifier and categorical levels for serving, and logs evaluation artifacts to MLflow. Live recommendation serving uses the classifier probability; the regressor is evaluated and logged but is not currently used by the recommendation endpoint.

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

The mock provider is deterministic and is the recommended default for local development and tests. To use Gemini, set the following values in the root `.env` before starting or restarting the API container:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-2.0-flash
```

Gemini credentials are read by the backend only when the Gemini provider is selected. Obtain a key from [Google AI Studio](https://aistudio.google.com/apikey), and do not commit it to the repository.

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

The backend suite currently contains 40 tests covering ingestion, feature leakage, temporal evaluation, leaderboard behavior, recommendation scoring, LLM validation, and API error handling. Continuous integration installs the backend and ML dependencies, enables pgvector, applies migrations, and runs the backend suite against PostgreSQL. The workflow is defined in [.github/workflows/ci.yml](.github/workflows/ci.yml).

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

The MVP intentionally does not yet include authentication, scheduled retraining or baseline refresh jobs, a production feedback-learning loop, an insights endpoint, recommendation history, real social-platform connectors, OAuth, automatic ingestion, or CSV import. "Daily recommendation" is currently a product concept: generation is manual and there is no scheduler or uniqueness rule.

The intended next steps are to harden the evaluation gate, add scheduled jobs and structured insights, implement recommendation feedback learning, and connect one real platform behind a shared ingestion interface.