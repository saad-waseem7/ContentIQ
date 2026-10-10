# Development guide

For people changing the code. Setup and operations are in [setup.md](setup.md), design background in [architecture.md](architecture.md).

## Repository layout

```text
backend/
  app/            FastAPI app: main.py, routers/, schemas.py, models.py, crud.py,
                  config.py, database.py, and the services for leaderboard,
                  insights (+ config and clustering) and recommendations
  features/       Performance metric, labels, content features, embeddings, topics
  ml/             Model config, data prep, training helpers, SHAP, inference, atomic writes
  llm/            LLMClient interface, prompt and validation (coach.py), Gemini and mock clients
  scripts/        Batch entry points (embeddings, baselines, features, training, MLflow check)
  migrations/     Alembic environment and 3 revisions
  tests/          pytest suite (20 test files plus conftest.py)
  data/           Generated artifacts, gitignored
frontend/
  app/            Pages: leaderboard, insights, recommend, history, plus layout and root redirect
  components/     UI components, skeletons
  lib/            API client and cache, React contexts, labels, chart theme
synthetic_data/   generator.py, config.py, validate.sql
.github/workflows/ci.yaml
docker-compose.yml
```

`backend/requirements.txt` includes `pytest`, so the test runner is in the production image. `requirements-ml.txt` adds the ML stack and pulls CPU-only PyTorch.

## Backend conventions

- **Settings** come from `app/config.py` (`pydantic-settings`). Real environment variables override `.env`. Required values have no defaults, so a missing one fails at import.
- **Services take plain data.** `leaderboard_service`, `insight_service` and `recommendation_service` hold the logic. Routers translate domain exceptions (`UnknownUserError`, `FeatureDataNotBuiltError`, `NoWinningContentError`, `ModelArtifactsNotFoundError`, `IdeaGenerationError`, `UserNotFoundError`, `UnknownRecommendationError`) into HTTP status codes.
- **Closed value lists** (platforms, content types, hook types) are defined once in `app/models.py` and reused by Pydantic schemas, the LLM output validator and the database CHECK constraints.
- **Artifacts are written atomically** through `ml/artifact_io.py`. Use it for any new file that the API reads.
- **Caches are keyed by file modification time** (feature table, classifier, category levels) or by a data fingerprint (niche clusters). If you add another cache, define how it invalidates before relying on it.

## Frontend state handling

All pages are client components under one root layout that wraps the app in three providers.

| Provider | State | Notes |
| --- | --- | --- |
| `UserContext` | The selected creator ID, a plain string | Initial value is `NEXT_PUBLIC_DEFAULT_USER_ID` or empty. Not persisted: a page reload loses it. |
| `RecommendationContext` | The recommendation currently shown on the Daily Recommendation page, and which user owns it | Cleared when the selected user changes. Late responses for a previously selected user are discarded. |
| `ThemeContext` | Light or dark | Stored in `localStorage` under `contentiq-theme`. |

The "Viewing user" box updates the selected ID on every keystroke, and each page fetches for the new value. Typing an ID character by character therefore sends a request per keystroke and mostly produces 404s. Paste the whole ID.

`lib/api.ts` is the only place that talks to the backend.

- GET calls go through `cachedGet`: a 30 second TTL keyed by full URL, with in-flight deduplication so two components asking for the same URL share one request. Failed requests are not cached.
- `POST /recommend` invalidates that user's cached history. The feedback call invalidates all cached history, because its response has no user ID.
- Leaderboard and Insights responses are cached for the TTL and are not invalidated by anything, so after rebuilding the feature table the browser can show old data for up to 30 seconds.
- Error messages are mapped from HTTP status in `components/StatusMessage.tsx`. FastAPI validation errors (a list) are joined into one string.

`NEXT_PUBLIC_*` values are inlined by Next.js when the dev server starts or the app is built. Restart the frontend after changing them.

## Common changes

| Change | What to touch |
| --- | --- |
| Add a platform, content type or hook type | `app/models.py` lists, a new Alembic migration for the CHECK constraints, `synthetic_data/config.py` if the generator should emit it, `frontend/lib/labels.ts`, then rebuild features and retrain. Existing model files will treat the new value as unseen. |
| Add or change a model feature | `features/` (compute it), `ml/config.py` (feature lists), `ml/idea_scoring.py` (inference row), then `build_features.py` and `train_model.py`. Keep training and serving construction identical, and check the leakage tests. |
| Change the label definition or the 3 and 10 post thresholds | `features/config.py` and `features/builder.py`, then rebuild and retrain. Update [ml-pipeline.md](ml-pipeline.md) and [insights-and-leaderboard.md](insights-and-leaderboard.md). |
| Add an Insights section | A function in `app/insight_service.py`, a threshold in `insight_config.py`, a field in the response and in `frontend/lib/api.ts`, then the page. |
| Change the LLM prompt or validation | `llm/coach.py` and its tests. Any new validation rule must also work with the mock client. |
| Use a different LLM provider | Implement `LLMClient.generate(prompt) -> str` (raise `LLMGenerationError` on provider failure) and select it in `llm/factory.py`. The router calls the factory once at import. |
| Change the database schema | Edit `app/models.py`, then `docker compose exec api alembic revision --autogenerate -m "message"`, review the generated file by hand, and `alembic upgrade head`. Autogenerate does not capture CHECK constraint changes reliably, so verify them. |
| Add an endpoint | A router under `app/routers/`, registered in `app/main.py`, a schema in `app/schemas.py`, a test, and an entry in [api-reference.md](api-reference.md). |

There is no linter, formatter or type checker configured for either side. Frontend TypeScript is type-checked as part of `npm run build`.

## Testing

### What exists

| Suite | Command (host) | Count | Where |
| --- | --- | --- | --- |
| Backend, pytest | `docker compose exec api pytest -q` | 164 tests | `backend/tests/` |
| Frontend, Vitest and React Testing Library | `docker compose exec frontend npm test` | 62 tests in 12 files | `__tests__/` folders under `frontend/` |

Counts come from collecting the suites in the handover review. How they ran:

- **Frontend:** all 62 passed in a scratch environment.
- **Backend:** 164 passed, eight consecutive runs, in a scratch environment with real PostgreSQL 16 with pgvector and a stubbed embedding model (the real model was not downloaded there). Dependency versions in that environment were newer than the pins in `requirements.txt` (for example FastAPI and pandas). The one flaky test found during the handover review was a defect in the test, not the product: its fake LLM assigned captions by call arrival order across parallel threads. It now keys each caption on the strategy directive in the prompt and passed 25 repeated runs. The project owner reported 156 passing under Docker before the handover changes. The Docker run was not repeated.

Backend coverage by area:

| Area | Test files |
| --- | --- |
| Feature leakage, labels, features, topics | `test_feature_leakage.py`, `test_topics.py` |
| Training helpers, evaluation, embedding reduction, atomic writes | `test_data_prep.py`, `test_evaluate.py`, `test_embedding_reduction.py`, `test_artifact_io.py` |
| Idea scoring | `test_idea_scoring.py` |
| LLM prompt, validation, retries, grounding | `test_llm_coach.py`, `test_gemini_client.py` |
| Services and endpoints | `test_leaderboard.py`, `test_insight_service.py`, `test_insight_clustering.py`, `test_insights_endpoint.py`, `test_recommendation_service.py`, `test_recommend_endpoint.py`, `test_recommendation_history.py`, `test_predict_endpoint.py`, `test_ingest.py`, `test_health.py` |

Frontend tests cover the four pages, the user selector and user switching, the recommendation context, the idea panel, the theme toggle, the API cache and error mapping, and label helpers. They mock `fetch`; none of them talks to a real backend.

### Not covered

- The batch scripts' database and MLflow flows (`build_features.py`, `generate_embeddings.py`, `train_model.py` end to end).
- Real Gemini calls. The Gemini client is tested against a fake model object only.
- Browser-level end-to-end flows and Docker Compose startup.
- Load, concurrency stress and security testing.

### Read this before running the backend suite

- **It writes to the database that `DATABASE_URL` points to.** Several tests create users, channels, content and recommendation rows through the application's session. `tests/conftest.py` deletes the users that appeared during the run when the session ends (foreign keys cascade). It does not run if the process is killed, and it would also delete a user someone ingests into the same database while the suite is running. Do not run the suite against a database you are demoing from or ingesting into.
- **It loads the real embedding model** in some tests, so the first run needs the model files (baked into the Docker image).
- **It needs the migrations applied** to the target database.

The safest pattern is still a throwaway database on the same server. Create it, point `DATABASE_URL` at it for one command, migrate and test:

```bash
docker compose exec db psql -U contentiq -d contentiq -c "CREATE DATABASE contentiq_test"
docker compose exec api sh -c 'export DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@db:5432/contentiq_test" && alembic upgrade head && pytest -q'
docker compose exec db psql -U contentiq -d contentiq -c "DROP DATABASE contentiq_test"
```

Replace `contentiq` with your `POSTGRES_USER` and `POSTGRES_DB` if you changed them. The mechanics (a second database, an overridden `DATABASE_URL`, migrate, then pytest) were verified outside Docker. This exact command sequence was not run inside the containers. `CREATE EXTENSION vector` runs inside the first migration, so the user needs permission to create it, which the default compose user has as the database owner and superuser.

Run one file or one test:

```bash
docker compose exec api pytest -q tests/test_llm_coach.py
docker compose exec api pytest -q tests/test_llm_coach.py -k fallback
```

Frontend, from the host (needs `npm ci` in `frontend/` first) or in the container:

```bash
cd frontend && npm test
```

### Continuous integration

`.github/workflows/ci.yaml` runs on pushes and pull requests to `main`, in two independent jobs.

- **test (backend):** Python 3.11, a `pgvector/pgvector:pg16` service with throwaway credentials, installs both requirements files, enables the extension, runs `alembic upgrade head` and then `pytest -v` from `backend/`. The job sets a dummy `MLFLOW_TRACKING_URI` and no LLM variables, so the mock client is used. This runs against a fresh database each time, so the test-data accumulation described above does not occur in CI.
- **frontend:** Node 20, `npm ci`, `npm test`, `npm run build`. The build downloads the Inter font from Google Fonts, so it needs internet.

CI does not run linters, security scans, the batch scripts or Docker builds. Whether the workflow currently passes on GitHub was not checked.

### Build notes

- `npm run build` run inside the live frontend container writes to `.next`, which the dev server is also using, and can leave it in a broken state until the container restarts. Build in a separate checkout or restart the container afterwards.
- Compose runs development servers (`uvicorn --reload`, `next dev`). There is no production Dockerfile or production compose file.
