# ContentIQ

**A personalized content performance coach.** ContentIQ compares each post with its creator's own history, then uses those patterns to evaluate content and suggest new ideas. It is built around synthetic data and is a working prototype, not a connected social publishing service.

The project is built end to end: synthetic data generation, leakage-safe feature engineering, ML training with SHAP-based interpretability, LLM-grounded recommendations, an Insight Engine, and a full-stack web application running in containers.

## What it does

- **Content Performance Leaderboard:** ranks posts relative to the creator's own baseline within platform and content type.
- **Insights:** shows personal hook, topic, and posting-time patterns, descriptive trends, monthly performance, niche comparisons, and topic clusters. Sample-size checks keep weak evidence from being presented as a firm finding.
- **Daily Recommendation:** creates three distinct candidates concurrently, grounds them in the creator's strongest posts, scores them with the trained classifier, and saves the top candidate.
- **Try Your Own Idea:** scores a creator-authored idea through the same model without saving it. The response notes when the topic is new to the model.
- **Recommendation feedback:** creators can mark recommendations as `actioned` or `dismissed`.
- **Recommendation History:** lists saved recommendations and their feedback status, newest first.

## Architecture

```text
Synthetic data generator --POST /ingest--> FastAPI REST API
                                                |
                                   PostgreSQL 16 + pgvector
                                                |
                              Leakage-safe temporal feature pipeline
                                                |
                              LightGBM classifier + regressor --MLflow
                                                |
                              SHAP analysis + planted-signal validation
                                                |
                  Gemini or deterministic mock LLM
                    grounded in leaderboard data
                                                |
                 3 candidates -> feature vectors -> classifier scores
                                                |
                         highest-scoring candidate persisted
                                                |
Next.js frontend <---------------- REST/JSON ----------------> FastAPI
```

The API, frontend, PostgreSQL, and MLflow run through Docker Compose. Database migrations, synthetic data generation, and model preparation are separate steps.

## Technology

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, SQLAlchemy, Pydantic, Alembic |
| Database | PostgreSQL 16 with pgvector |
| Machine learning | LightGBM, scikit-learn, SHAP, sentence-transformers |
| Embeddings | `all-MiniLM-L6-v2` with 384-dimensional caption vectors |
| Experiment tracking | MLflow |
| LLM | Provider-agnostic interface, deterministic mock client, Google Gemini |
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS, Recharts |
| Testing | pytest, Vitest, React Testing Library |
| CI and infrastructure | GitHub Actions, Docker Compose |

## How it works

- Training features use only information available before each post. Tests check that later posts cannot leak into earlier features or labels.
- Performance is compared with each creator's prior history within platform and content type. Insights use validated rows, clear sample thresholds, and descriptive rather than causal language.
- Recommendation topics are normalized for model scoring. Prompts use the creator's observed platform, formats, and topics, and generated rationales are checked against the cited posts.
- Niche-level topic clusters are cached and refreshed when embeddings or feature data change.
- Candidate posting-time features use the creator's historically strongest posting time, so a score does not depend on when a request was made.
- Gemini calls use a configurable deadline and app-managed retries. Ingestion and prediction requests also enforce text and list-size limits.
- Training reports classifier and regressor metrics, baseline comparisons, and SHAP checks. Model and feature updates are written atomically to avoid exposing partial files during a rebuild.

## Project structure

```text
backend/
  app/          FastAPI routes, services, ORM models, and Insight Engine
  features/     Leakage-safe feature engineering, embeddings, topic normalization, and baselines
  ml/           Model training, evaluation, SHAP, inference, and safe artifact writes
  llm/          Provider-agnostic client, prompt construction, and guardrails
  migrations/   Alembic schema migrations
  scripts/      Feature, embedding, baseline, training, and evaluation jobs
  tests/        Backend unit and integration tests
synthetic_data/ Synthetic creator, content, metric, and planted-signal generator
frontend/       Next.js screens, components, API helpers, and shared user/theme state
.github/        CI workflows
docker-compose.yml
```

## Running locally

### Prerequisites

- Docker and Docker Compose
- Git
- Python 3.11 or later for the synthetic data generator
- Node.js 20 or later only if running the frontend outside Docker

The frontend, backend, PostgreSQL, and MLflow services run in Docker.

On Linux, check whether a native PostgreSQL installation is already using port 5432:

```bash
sudo ss -tlnp | grep 5432
```

If it is, set `POSTGRES_PORT=5433` in `.env`. `DATABASE_URL` should still use `db:5432`, because it is resolved inside the Docker network.

### Start the application

From the repository root:

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
```

On Windows, use `Copy-Item .env.example .env` instead of `cp`.

The root `.env` supplies settings to Docker Compose and the API container. It is local configuration and is not committed. The default LLM provider is `mock` and needs no API key. To use Gemini, see [LLM configuration](#llm-configuration).

The root template is for the Docker Compose stack. The tracked `backend/.env.example` and `frontend/.env.local.example` show optional per-service settings. The frontend defaults to the local API address and does not need a separate environment file for the Compose setup.

The Compose stack starts all services together:

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- MLflow: http://localhost:5001
- PostgreSQL: `localhost:${POSTGRES_PORT}`

No separate frontend or backend startup command is required. Migrations are not applied automatically, so run the Alembic command when creating a database or applying a schema change.

### Generate synthetic data

The generator creates multi-niche creator data with planted performance effects and sends it to the running API through `/ingest`.

```bash
python3.11 -m venv synthetic_data/venv
source synthetic_data/venv/bin/activate
pip install -r synthetic_data/requirements.txt
python synthetic_data/generator.py
```

On Windows, activate the environment with `synthetic_data\\venv\\Scripts\\activate`.

### Build features and train the model

Run these commands after data has been ingested:

```bash
docker compose exec api python scripts/compute_baselines.py
docker compose exec api python scripts/generate_embeddings.py
docker compose exec api python scripts/build_features.py
docker compose exec api python scripts/train_model.py
```

Run the full pipeline before using the leaderboard, insights, recommendation, and prediction flows. Repeat it after creating a fresh database or changing ingested data. The trained classifier scores recommendations and custom ideas.

Optional commands:

```bash
docker compose exec api python scripts/verify_mlflow.py
docker compose exec api python scripts/train_model_pca_experiment.py
```

The PCA command is an evaluation experiment and does not replace the serving model.

## LLM configuration

The default `mock` provider is deterministic and requires no API key. It is recommended for local development and tests.

To use Google Gemini, set these values in the root `.env` file and restart the API container:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-3.6-flash
GEMINI_TIMEOUT_SEC=30
```

The model name and request timeout are configurable. Gemini requests default to a 30-second timeout, and the application controls retries. Obtain keys from [Google AI Studio](https://aistudio.google.com/apikey), and never commit the key to the repository. Provider failures, blocked responses, invalid JSON, and schema violations are surfaced through the recommendation API's error handling.

## Data and model pipeline

1. Synthetic data or a future connector sends users, channels, content, and metric snapshots to `/ingest`.
2. Caption embeddings are generated with `all-MiniLM-L6-v2` and stored in PostgreSQL with pgvector.
3. Baselines and features are built from each creator's prior history.
4. Raw performance is calculated as `(likes + comments + shares + saves) / reach`.
5. Over-performer labels compare a post with its historical `(user, platform, content_type)` baseline.
6. `train_model.py` performs a temporal per-user split and trains LightGBM classifier and regressor models.
7. The classifier and categorical levels are saved for serving. MLflow receives metrics, models, SHAP outputs, and the data snapshot hash.
8. Recommendations retrieve top-performing posts, generate three grounded ideas concurrently, score every candidate using the same feature space, and persist only the winner.

Every temporal feature and baseline used for a post is computed without looking beyond that post's publication time. Posts without enough prior history remain in the dataset but cannot receive a reliable relative-performance label or leaderboard rank.

## API overview

Full request and response schemas are available in Swagger at http://localhost:8000/docs.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check API and database connectivity |
| `POST` | `/ingest` | Create or update users, channels, content, and metrics |
| `GET` | `/content?user_id={uuid}` | Return a creator's relative-performance leaderboard |
| `GET` | `/insights?user_id={uuid}` | Return personal, trend, niche, and topic-cluster insights |
| `POST` | `/recommend?user_id={uuid}` | Generate, score, and persist the best recommendation candidate |
| `GET` | `/recommendations?user_id={uuid}` | Return the user's recommendation history, newest first |
| `POST` | `/predict?user_id={uuid}` | Score a user-authored idea and report whether its topic is known |
| `POST` | `/recommendations/{id}/feedback` | Mark a recommendation `actioned` or `dismissed` |

Build features before using the leaderboard or insights. Recommendations and custom prediction also need the trained classifier and enough top-performing history for the selected user. Invalid or unknown IDs return a not-found response before recommendation generation can make an LLM call. Ingestion validates supported categories, parent IDs, and metric timestamps. Text fields have explicit limits, including 5,000 characters for captions, 300 for titles, and up to 100 topic tags or hashtags per post. Oversized requests are rejected with HTTP 422.

## Frontend

The frontend is included in Docker Compose and is available at http://localhost:3000. The root route redirects to the leaderboard.

Current screens include:

- **Leaderboard:** relative-performance ranking for a manually entered user UUID.
- **Insights:** personal hook, topic, and posting-time patterns, monthly trends, niche comparison, and topic clusters.
- **Daily Recommendation:** three-candidate generation behind the API, display of the selected idea and predicted score, plus feedback actions.
- **Recommendation History:** previously generated recommendations with their predicted scores and statuses.
- **Try Your Own Idea:** on-demand scoring on the recommendation page, without saving the idea.
- Loading, empty, and error states, responsive layouts, dark mode, and protection against stale results when switching users.

Run frontend checks in the running container:

```bash
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

## Testing and CI

```bash
docker compose exec api pytest -v
docker compose exec frontend npm test
```

The backend suite covers ingestion limits, temporal splitting, feature leakage, embeddings, clustering, insights, model scoring, recommendation selection, LLM timeouts and validation, and API errors. GitHub Actions runs the backend tests against PostgreSQL with pgvector, then runs frontend tests and a production build. See [.github/workflows/ci.yaml](.github/workflows/ci.yaml).

The training pipeline evaluates the classifier against a content-type baseline, reports regressor performance, and checks SHAP values for recovery of the planted signal. Results are recorded in MLflow and depend on the generated data and training configuration.

## Current limits

This is a prototype built around synthetic data. It has no authentication, real social-platform connectors, automatic ingestion, scheduled retraining, or feedback-driven model updates. Do not expose it as a shared service without adding authentication and reviewing external API usage.