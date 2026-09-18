# ContentIQ

**A personalized content performance coach.** ContentIQ learns what works for an individual creator instead of applying generic best practices. It models each post against that creator's own historical baseline, then uses that model to generate, rank, and score new content ideas.

The project is built end to end: synthetic data generation, leakage-safe feature engineering, ML training with SHAP-based interpretability, LLM-grounded recommendations, an Insight Engine, and a full-stack web application running in containers.

## What it does

- **Content Performance Leaderboard:** ranks posts relative to the creator's own baseline within platform and content type.
- **Insights:** shows personal patterns across content type, hook, topic, and posting time; non-causal trends; niche-population comparisons; and niche-scoped topic clusters built with KMeans over caption embeddings.
- **Daily Recommendation:** asks the configured LLM for three strategically distinct candidates, scores every candidate with the trained classifier, and persists the highest-scoring idea with a data-grounded rationale.
- **Try Your Own Idea:** `POST /predict` scores a creator-authored idea against the same feature and model pipeline without persisting it as a recommendation.
- **Recommendation feedback:** creators can mark recommendations as `actioned` or `dismissed`.
- **Recommendation History:** lists a user's saved recommendations from newest to oldest.

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

All application services run through Docker Compose. Database migrations, synthetic data generation, and model preparation are explicit pipeline commands rather than container startup tasks.

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
- **Honest evaluation:** the classifier is evaluated with a temporal per-user split and compared against a content-type-average baseline. The regressor's weaker Spearman result is retained as a documented limitation rather than hidden.
- **Diverse recommendation candidates:** three LLM calls run concurrently, each with a distinct safe, alternative, or experimental strategy directive. Candidates are independently featureized and scored before selection.
- **Stable recommendation scoring:** posting-time features use the user's historically best-performing hour and weekday. This prevents the same idea from receiving different scores simply because it was requested at a different time.
- **Provider-agnostic LLM integration:** the recommendation pipeline depends on `LLMClient`, not a vendor SDK. The deterministic mock supports full local testing, while Gemini can be enabled through configuration.
- **Structured LLM guardrails:** responses must be valid JSON using the backend's supported platform, content-type, and hook-type values. Invalid output is retried, and rationales must contain a numeric citation from the grounding data.
- **Reproducible experiments:** MLflow records the data snapshot hash, parameters, metrics, trained models, feature importance, and SHAP artifacts.
- **PCA experiment retained separately:** embedding reduction is implemented for evaluation but is not part of the shipped serving pipeline.

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
frontend/       Next.js leaderboard, insights, recommendation, and predict UI
docs/           Demo walkthrough and known limitations
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

The project uses two `.env` files when running the Python application locally or from its mounted container directory. The root `.env` configures Docker Compose; `backend/.env` is read by the application itself. Keep both complete copies of the required database and MLflow settings if you create `backend/.env` directly:

```bash
cp .env.example backend/.env
```

Add any `LLM_PROVIDER`, `GEMINI_API_KEY`, and `GEMINI_MODEL` values to the appropriate environment as well. Never commit either file.

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

The pipeline creates or updates:

- `backend/data/features.parquet`
- `backend/data/classifier.joblib`
- `backend/data/category_levels.json`
- MLflow runs and artifacts in the configured tracking store

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

The leaderboard, insights, recommendation, and predict endpoints require the generated feature artifacts. Recommendations and custom prediction also require sufficient winning history for the selected user. Ingestion validates supported platforms, content types, hook types, parent IDs, and metric timestamps.

## Frontend

The frontend is included in Docker Compose and is available at http://localhost:3000. The root route redirects to the leaderboard.

Current screens include:

- **Leaderboard:** relative-performance ranking for a manually entered user UUID.
- **Insights:** personal patterns, topic performance, trends, niche comparison, and topic clusters.
- **Daily Recommendation:** three-candidate generation behind the API, display of the selected idea and predicted score, plus feedback actions.
- **Recommendation History:** previously generated recommendations with their predicted scores and statuses.
- **Predict:** on-demand scoring for a creator's own idea.
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

The backend suite covers ingestion, temporal splitting, feature leakage, embeddings, clustering, insights, model scoring, leaderboard behavior, recommendation selection, LLM validation, and API error handling. GitHub Actions runs the backend suite against a clean PostgreSQL and pgvector service, applies migrations, and installs the ML dependencies. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

The full pipeline has also been reproduced from a clean database on Windows, Fedora, and Ubuntu. The main user-facing flows, including recommendation history and feedback, were manually verified end to end.

## Model results

Latest project evaluation results are summarized below. Results may vary when the synthetic dataset or training configuration changes.

| Metric | Result | Target |
| --- | --- | --- |
| Classifier ROC-AUC | approximately 0.74-0.75 | at least 0.70 |
| Classifier vs. content-type baseline | beats baseline | pass |
| Regressor Spearman rho | approximately 0.32-0.36 | at least 0.40; documented gap |
| Planted signal recovery via SHAP | confirmed across five niches | pass |

The regressor gap is retained as an honest limitation. The PCA-on-embeddings experiment was measured and found to slightly regress the headline metrics, so it remains available for reproducibility but is not used in production serving.

Recommendation diversity was evaluated with live Gemini output. Moving from one shared prompt to three distinct strategy directives eliminated identical hooks and topics across all candidates, increased the average classifier score spread from 0.076 to 0.295, and improved the rate at which the winner matched a standout personal pattern from 88% to 100%.

## Documentation

- [Demo script](docs/DEMO_SCRIPT.md): a 10-15 minute walkthrough of the full system.
- [Known limitations](docs/KNOWN_LIMITATIONS.md): current product and modeling gaps and why they are deferred.
- [Final project status](docs/FINAL_PROJECT_STATUS.md): implementation summary, validation results, and deferred scope.

## Scope and roadmap

The current MVP does not include authentication, scheduled retraining or baseline refresh jobs, production feedback learning, OAuth, real social-platform connectors, automatic ingestion, or CSV import. Daily recommendations are generated manually through the endpoint. There is no scheduler or uniqueness rule for recommendations.

The next product steps are scheduled baseline and retraining jobs, stronger feedback-loop learning, connector abstractions with one real platform, and continued evaluation hardening.