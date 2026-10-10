# ContentIQ

ContentIQ is a personalized content performance coach for creators. It measures every post against the creator's own history instead of a global average, shows which hooks, topics and posting times have worked for that creator, and proposes new post ideas that an LLM drafts and a trained model ranks.

This repository is a complete working prototype: a synthetic data generator, a FastAPI backend, PostgreSQL with pgvector, a LightGBM training pipeline, an LLM layer (Google Gemini or a deterministic mock) and a Next.js frontend. It runs on synthetic data only. There is no real platform connector and no authentication.

## What it does

| Screen | What it shows |
| --- | --- |
| Leaderboard | A creator's posts ranked by how far they beat that creator's own earlier posts of the same platform and format. |
| Insights | Personal hook, topic and posting-time patterns, a recent-versus-earlier trend, monthly performance, a comparison with other creators in the niche, and topic clusters. |
| Daily Recommendation | Three LLM-drafted ideas grounded in the creator's best posts. Each is scored by the classifier and only the highest-scoring one is saved. The creator can mark it actioned or dismissed. |
| Try Your Own Idea | Scores an idea the user types in, using the same model. Nothing is saved. |
| History | Saved recommendations for the selected creator, newest first, with score and status. |

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic |
| Database | PostgreSQL 16 with the pgvector extension |
| ML | LightGBM, scikit-learn, SHAP, sentence-transformers (`all-MiniLM-L6-v2`), VADER, MLflow |
| LLM | Gemini through `google-generativeai`, or a built-in mock client |
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Recharts |
| Tests and CI | pytest, Vitest with React Testing Library, GitHub Actions |
| Runtime | Docker Compose (database, API, MLflow, frontend) |

## Architecture

```text
synthetic_data/generator.py --POST /ingest--> FastAPI --> PostgreSQL + pgvector
                                                              |
                          batch scripts (backend/scripts), run by hand
                          embeddings -> features.parquet -> classifier.joblib
                                                              |
Next.js  <---- JSON over HTTP ---->  FastAPI  <--- reads --- backend/data/*
                                        |
                                        +--> Gemini or mock LLM (recommendations only)
```

The API serves reads from precomputed files in `backend/data/`, not from live queries over the metrics tables. PostgreSQL holds the raw data, the caption embeddings and the saved recommendations. Details are in [docs/architecture.md](docs/architecture.md).

## Prerequisites

- Docker with Compose v2 (`docker compose`).
- Python 3.10 or newer on the host, only to run the data generator (it needs `requests` and `numpy`).
- Node.js 20 or newer on the host, only if you run frontend tooling outside Docker.
- Internet access while building. The API image installs PyTorch (CPU) and downloads the embedding model, and `next build` fetches the Inter font from Google Fonts.

## Setup

Commands are marked **host** (your shell, repository root) or **api container** (run through `docker compose exec`).

**1. Create the environment file (host).**

```bash
cp .env.example .env
```

On Windows PowerShell use `Copy-Item .env.example .env`. Change the password in `.env`. If port 5432 is already used on your machine, set `POSTGRES_PORT=5433` (or any free port) in `.env`. Leave the port inside `DATABASE_URL` at `5432`, because that URL is used inside the Docker network. The default LLM provider is the mock, so no API key is needed to get started.

**2. Start the stack (host).**

```bash
docker compose up --build -d
```

**3. Apply database migrations (api container).** Migrations are never applied automatically.

```bash
docker compose exec api alembic upgrade head
```

**4. Generate synthetic data (host).** The API from step 2 must be running, because the generator posts to `http://localhost:8000/ingest`. It creates 5 niches x 25 creators with 150 to 200 posts each, about 21.5k posts in total.

```bash
python3 -m venv synthetic_data/venv
source synthetic_data/venv/bin/activate        # Windows: synthetic_data\venv\Scripts\activate
pip install -r synthetic_data/requirements.txt
python synthetic_data/generator.py
```

The generator is not idempotent. Running it again adds another full set of creators. Expect it to take several minutes, because it sends one HTTP request per post.

**5. Build baselines, embeddings, features and the model (api container).** Run these in order.

```bash
docker compose exec api python scripts/compute_baselines.py
docker compose exec api python scripts/generate_embeddings.py
docker compose exec api python scripts/build_features.py
docker compose exec api python scripts/train_model.py
```

`compute_baselines.py` fills the `user_baselines` table, which the application does not read today, so it can be skipped. The other three are required. `train_model.py` needs the MLflow container from step 2 to be reachable, and it prints its acceptance checks at the end. Repeat step 5 whenever data is added or changed. See [docs/setup.md](docs/setup.md) for what each script reads and writes.

**6. Pick a creator and open the app.** The frontend has no user list. Paste a user ID into the "Viewing user" box. List some creators with plenty of history (host):

```bash
docker compose exec db psql -U contentiq -d contentiq -c "SELECT u.id, u.niche, ch.platform, count(c.id) AS posts FROM users u JOIN channels ch ON ch.user_id = u.id JOIN content c ON c.channel_id = ch.id GROUP BY u.id, u.niche, ch.platform ORDER BY posts DESC LIMIT 10;"
```

Use your own `POSTGRES_USER` and `POSTGRES_DB` if you changed them.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| MLflow | http://localhost:5001 |
| PostgreSQL | `localhost:${POSTGRES_PORT}` |

## Configuration

Docker Compose loads the root `.env` into the database and API containers. The API also reads `backend/.env` if it exists, but values already set in the container environment win over that file.

| Variable | Purpose |
| --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` | Database credentials and the host port Compose publishes. |
| `DATABASE_URL` | Connection string used by the API. Host must be `db`, port `5432`. |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` inside Docker. |
| `LLM_PROVIDER` | `mock` (default) or `gemini`. Any other value silently selects the mock. |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_TIMEOUT_SEC` | Used only when `LLM_PROVIDER=gemini`. The timeout defaults to 30 seconds. |

To use Gemini, add these lines to the root `.env` and recreate the API container with `docker compose up -d --force-recreate api`:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_from_google_ai_studio
GEMINI_MODEL=a_model_name_your_key_can_use
```

The tracked `backend/.env.example` and `frontend/.env.local.example` are not ready to copy as they are. `backend/.env.example` points `DATABASE_URL` at port 5433 and selects Gemini, and `frontend/.env.local.example` contains placeholder URLs. You do not need either file for the Docker setup. [docs/setup.md](docs/setup.md#environment-files) explains how to use them safely. Never commit `.env`, `backend/.env` or `frontend/.env.local`; all three are gitignored.

## Tests

```bash
docker compose exec api pytest -q            # backend, 156 tests
docker compose exec frontend npm test        # frontend, 62 tests
```

The backend suite writes rows to the database that `DATABASE_URL` points at and loads the real embedding model. Read [docs/development.md](docs/development.md#testing) before running it against data you care about.

## Documentation

| Document | Contents |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Components, Docker topology, database schema, where state lives, caching, pgvector usage. |
| [docs/setup.md](docs/setup.md) | Environment files, pipeline refresh, resetting, running without Docker, troubleshooting. |
| [docs/api-reference.md](docs/api-reference.md) | Every endpoint, with parameters, responses, limits and error behavior. |
| [docs/ml-pipeline.md](docs/ml-pipeline.md) | Synthetic data, performance metric, leakage-safe labels, features, training, evaluation, artifacts. |
| [docs/recommendations.md](docs/recommendations.md) | Grounding, LLM validation and fallbacks, scoring and ranking, custom idea scoring. |
| [docs/insights-and-leaderboard.md](docs/insights-and-leaderboard.md) | How each Leaderboard and Insights number is computed and how to read it. |
| [docs/development.md](docs/development.md) | Repository layout, frontend state handling, common changes, testing and CI. |
| [docs/demo-guide.md](docs/demo-guide.md) | A walkthrough for demonstrating the application. |
| [docs/limitations.md](docs/limitations.md) | Limitations, security considerations, defects found during the handover review, deferred work. |

## Important limitations

- The data is synthetic and contains a deliberately planted signal, so model metrics show that the pipeline recovers that signal, not how it would perform on real creators.
- There is no authentication. Anyone who can reach the API can read any creator's data, write through `/ingest`, and trigger LLM calls.
- Features and model files are rebuilt by hand. New ingested data does not appear in the leaderboard, insights or recommendations until `build_features.py` runs, and the model does not learn from it until `train_model.py` runs.
- The compose setup is a development setup: hot-reload servers, a published database port and a default password.

The full list, including defects found while preparing this handover, is in [docs/limitations.md](docs/limitations.md).