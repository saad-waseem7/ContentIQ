# ContentIQ

**A personalized content performance coach.** ContentIQ learns what works for each creator by comparing posts with that creator's own history, then uses the resulting model to generate, rank, and score new content ideas.

The project is built end to end: synthetic data generation, leakage-safe feature engineering, ML training with SHAP-based interpretability, LLM-grounded recommendations, an Insight Engine, and a full-stack web application running in containers.

## What it does

- **Content Performance Leaderboard:** ranks posts relative to the creator's own baseline within platform and content type.
- **Insights:** shows personal patterns across content type, hook, topic, and posting time; non-causal trends; niche-population comparisons; and niche-scoped topic clusters built with KMeans over caption embeddings.
- **Daily Recommendation:** generates three strategically distinct candidates, scores each with the trained classifier, and saves the highest-scoring idea with a rationale grounded in the creator's data.
- **Try Your Own Idea:** a panel on the recommendation page scores a creator-authored idea through the same model without saving it as a recommendation.
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

The API, frontend, PostgreSQL, and MLflow run through Docker Compose. Database migrations, synthetic data generation, and model preparation are separate commands.

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

## Engineering highlights

- **Leakage-safe feature pipeline:** training features use an expanding window of strictly prior posts. Dedicated tests verify that future metrics cannot affect an earlier post's features or label.
- **Planted-signal validation:** the synthetic dataset injects niche-specific `(hook_type, topic)` effects. SHAP analysis compares matching and non-matching rows within each niche to verify that the model recovers the signal.
- **Model evaluation:** the classifier is evaluated with a temporal per-user split and compared against a content-type-average baseline. The training run also reports regressor performance and checks for recovery of the planted signal.
- **Diverse recommendation candidates:** three LLM calls run concurrently, each with a distinct safe, alternative, or experimental strategy directive. Candidates are independently featureized and scored before selection.
- **Stable recommendation scoring:** posting-time features use the user's historically best-performing hour and weekday, so scores do not change just because an idea was requested at a different time.
- **Provider-agnostic LLM integration:** the recommendation pipeline depends on `LLMClient`, not a vendor SDK. The deterministic mock supports full local testing, while Gemini can be enabled through configuration.
- **Structured LLM guardrails:** responses must be valid JSON using the backend's supported platform, content-type, and hook-type values. Invalid output is retried, and rationales must contain a numeric citation from the grounding data.
- **Reproducible experiments:** MLflow records the data snapshot hash, parameters, metrics, trained models, feature importance, and SHAP artifacts.
- **Evaluation tools:** the PCA-on-embeddings experiment is available separately and is not part of the serving pipeline.

## Project structure

```text
backend/
  app/          FastAPI routes, services, ORM models, and Insight Engine
  features/     Leakage-safe feature engineering, embeddings, and baselines
  ml/           Model training, evaluation, SHAP, inference, and idea scoring
  llm/          Provider-agnostic client, prompt construction, and guardrails
  migrations/   Alembic schema migrations
  scripts/      Feature, embedding, baseline, training, and evaluation jobs
  tests/        Backend unit and integration tests
synthetic_data/ Synthetic creator, content, metric, and planted-signal generator
frontend/       Next.js app, components, and shared API/state utilities
.github/        CI workflows
docker-compose.yml
```

## Running locally

### Prerequisites

- Docker and Docker Compose
- Git
- Python 3.11 or later for the synthetic data generator

The frontend, backend, PostgreSQL, and MLflow services run in Docker. Node.js is only needed when working on the frontend outside its container.

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

Run the full pipeline before using the leaderboard, insights, recommendation, and prediction flows. Repeat it after creating a fresh database or changing the ingested data. The trained classifier scores recommendations and custom ideas.

Optional commands:

```bash
docker compose exec api python scripts/verify_mlflow.py
docker compose exec api python scripts/evaluate_recommendations.py
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
```

The model name is configurable. Obtain keys from [Google AI Studio](https://aistudio.google.com/apikey), and never commit the key to the repository. Gemini failures, blocked responses, invalid JSON, and schema violations are surfaced through the recommendation API's error handling.

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

## Environment variables

The root `.env` file is based on [.env.example](.env.example):

| Variable | Purpose |
| --- | --- |
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_DB` | PostgreSQL database name |
| `POSTGRES_PORT` | Host port mapped to PostgreSQL |
| `DATABASE_URL` | SQLAlchemy database URL |
| `MLFLOW_TRACKING_URI` | MLflow tracking endpoint |
| `LLM_PROVIDER` | `mock` by default; use `gemini` for Gemini |
| `GEMINI_API_KEY` | Required when Gemini is selected |
| `GEMINI_MODEL` | Configurable Gemini model name |

The frontend uses `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000`, and optionally `NEXT_PUBLIC_DEFAULT_USER_ID`. The Docker Compose frontend already uses the default API URL.

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
| `POST` | `/predict?user_id={uuid}` | Score a user-authored idea without persisting it |
| `POST` | `/recommendations/{id}/feedback` | Mark a recommendation `actioned` or `dismissed` |

Build features before using the leaderboard or insights. Recommendations and custom prediction also need the trained classifier and enough top-performing history for the selected user. Ingestion validates supported platforms, content types, hook types, parent IDs, and metric timestamps.

## Frontend

The frontend is included in Docker Compose and is available at http://localhost:3000. The root route redirects to the leaderboard.

Current screens include:

- **Leaderboard:** relative-performance ranking for a manually entered user UUID.
- **Insights:** personal patterns, topic performance, trends, niche comparison, and topic clusters.
- **Daily Recommendation:** three-candidate generation behind the API, display of the selected idea and predicted score, plus feedback actions.
- **Recommendation History:** previously generated recommendations with their predicted scores and statuses.
- **Try Your Own Idea:** on-demand scoring on the recommendation page, without saving the idea.
- Loading, empty, error, responsive, and dark-mode states.

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

The backend suite covers ingestion, temporal splitting, feature leakage, embeddings, clustering, insights, model scoring, leaderboard behavior, recommendation selection, LLM validation, and API error handling. GitHub Actions runs the backend tests against PostgreSQL with pgvector, then runs frontend tests and a production build. See [.github/workflows/ci.yaml](.github/workflows/ci.yaml).

The training pipeline evaluates the classifier against a content-type baseline, reports regressor performance, and checks SHAP values for recovery of the planted signal. Results are recorded in MLflow and depend on the generated data and training configuration.

## Current limits

This is a prototype built around synthetic data. It has no authentication, real social-platform connectors, automatic ingestion, scheduled retraining, or feedback-driven model updates. Do not expose it as a shared service without adding authentication and reviewing external API usage.