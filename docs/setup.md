# Setup and operations

The README has the shortest path to a running system. This document covers configuration in detail, what each pipeline script does, how to refresh or reset data, how to run without Docker, and what to do when something fails.

## Environment files

Three files can hold configuration. All three are gitignored. Only the `.example` templates are tracked.

| File | Read by | Needed for Docker setup |
| --- | --- | --- |
| `.env` (repository root) | Docker Compose, which injects it into the `db` and `api` containers and uses it to fill `${...}` placeholders | Yes |
| `backend/.env` | The API itself, from `/app/.env` inside the container (the working directory is `/app`) | No |
| `frontend/.env.local` | Next.js | No |

The API's settings class (`backend/app/config.py`) reads real environment variables first and `.env` in its working directory second. In Docker, anything in the root `.env` is already an environment variable, so it wins over `backend/.env`. Put everything in the root `.env` and you can ignore the other two files.

### Variable reference

| Variable | Required | Default | Used by |
| --- | --- | --- | --- |
| `POSTGRES_USER` | Yes | none | `db` container; API settings |
| `POSTGRES_PASSWORD` | Yes | none | `db` container; API settings |
| `POSTGRES_DB` | Yes | none | `db` container; API settings |
| `POSTGRES_PORT` | Compose only | none | Host port published for the database. Compose fails to interpolate the port mapping if it is unset. |
| `DATABASE_URL` | Yes | none | API, Alembic, scripts. Inside Docker the host is `db` and the port is `5432` regardless of `POSTGRES_PORT`. |
| `MLFLOW_TRACKING_URI` | Yes | none | `train_model.py`, `verify_mlflow.py`. `http://mlflow:5000` inside Docker. |
| `LLM_PROVIDER` | No | `mock` | `mock` or `gemini`, case-insensitive. Any other value stops the API at startup with `LLM_PROVIDER must be one of ...`. |
| `GEMINI_API_KEY` | When `LLM_PROVIDER=gemini` | empty | Gemini client |
| `GEMINI_MODEL` | No | `gemini-3.6-flash` | Gemini client. Set it to a model your key can call. |
| `GEMINI_TIMEOUT_SEC` | No | `30` | Per-call deadline in seconds for each Gemini request |
| `NEXT_PUBLIC_API_BASE_URL` | No | `http://localhost:8000` | Frontend. Must be reachable from the browser. |
| `NEXT_PUBLIC_DEFAULT_USER_ID` | No | empty | Frontend. Prefills the "Viewing user" box. |

The five required API variables (`DATABASE_URL`, the three `POSTGRES_*` names and `MLFLOW_TRACKING_URI`) have no defaults. If any is missing the API, Alembic and every script fail on import with a Pydantic `ValidationError` that lists the missing fields.

### Using the example files safely

- **Root `.env.example`.** Copy it to `.env` and change the password. Keep `DATABASE_URL` consistent with the user, password and database name you set. If 5432 is busy on the host, change only `POSTGRES_PORT`.
- **`backend/.env.example`.** Optional. It is meant for running the API outside Docker: `DATABASE_URL` points at `localhost:5432` and `MLFLOW_TRACKING_URI` at `http://localhost:5001`, and the LLM is the mock. Adjust the port to your `POSTGRES_PORT`. Inside Docker the root `.env` wins over this file, so copying it there is harmless but pointless.
- **`frontend/.env.local.example`.** Optional. It points the browser at `http://localhost:8000`, which is what the Docker setup publishes. `NEXT_PUBLIC_DEFAULT_USER_ID` is commented out. Next.js reads the file when the dev server starts, so restart the frontend container after editing.
- Never commit real values. `.env`, `backend/.env` and `frontend/.env.local` are covered by `.gitignore`, but check `git status` before committing.

### Gemini

1. Create a key in Google AI Studio.
2. Add `LLM_PROVIDER=gemini`, `GEMINI_API_KEY` and a `GEMINI_MODEL` your key can call to the root `.env`.
3. Recreate the API container so it re-reads the environment: `docker compose up -d --force-recreate api`. `docker compose restart api` does not reload `.env`.

Each Gemini call has the configured timeout and the SDK's own retry is switched off. The application retries instead: each candidate gets up to two attempts, and a recommendation generates three candidates in parallel, so one request makes at most six Gemini calls and a stalled provider is bounded to about two timeouts. The free tier has a small daily quota (the maintainers saw roughly 20 requests per day), so a few recommendations can exhaust it. If Gemini is unavailable, set `LLM_PROVIDER=mock` and recreate the API container. Scoring, leaderboard and insights do not depend on the LLM.

## Pipeline reference

All scripts live in `backend/scripts` and run inside the `api` container as `docker compose exec api python scripts/<name>.py`.

| Script | Reads | Writes | Notes |
| --- | --- | --- | --- |
| `compute_baselines.py` | Latest metric snapshot per post, from PostgreSQL | `user_baselines` rows (upsert) | Median, 25th and 75th percentile per creator, platform and format, for groups with at least 3 posts. No application code reads this table. |
| `generate_embeddings.py` | Posts with `caption_embedding IS NULL` | `content.caption_embedding` | Text is title plus caption. Posts with neither are skipped. Safe to rerun: it only fills missing vectors. |
| `build_features.py` | Users, channels, content, latest metric snapshot, embeddings | `backend/data/features.parquet` | Rewrites the whole table. Prints row count (39 columns) and labeled-row count. |
| `train_model.py` | `features.parquet` | `classifier.joblib`, `category_levels.json`, one MLflow run | Needs the MLflow server. See the note below. |
| `verify_mlflow.py` | none | One MLflow smoke run | Connectivity check only. |
| `train_model_pca_experiment.py` | `features.parquet`, embeddings from PostgreSQL | `backend/data/experiments/` | Optional experiment. Does not touch the serving model. |

`train_model.py` writes the serving files before it computes evaluation metrics, SHAP values or the MLflow run. If it fails later (for example because the MLflow server is down), the new `classifier.joblib` and `category_levels.json` are already in place. The PASS and FAIL lines it prints at the end are informational and do not stop or roll back anything.

The two model files must come from the same run. Copying only one of them gives the classifier a different category vocabulary than it was trained with.

### When to rerun what

| You did this | Rerun |
| --- | --- |
| Ingested new posts or metrics | `generate_embeddings.py`, `build_features.py`. Rerun `train_model.py` if the model should learn from them. |
| Ingested new creators | Same as above. New creators get a 404 from the leaderboard until `build_features.py` has run. |
| Changed feature code or `ml/config.py` | `build_features.py` if the feature table changed, then `train_model.py`. |
| Changed only `LLM_*` settings | Recreate the API container. |
| Retrained the model | Nothing. The API notices the new file by its modification time on the next request. |

## Resetting state

| Goal | Command (host) | Effect |
| --- | --- | --- |
| Stop services, keep data | `docker compose down` | Containers removed, volumes kept. |
| Wipe the database and MLflow history | `docker compose down -v` | Deletes the `pgdata` and `mlflow_data` volumes. |
| Start fresh after a wipe | `docker compose up --build -d`, then `alembic upgrade head`, generator, pipeline | See the README. |

`backend/data/` is on your host and is not removed by `down -v`. After a database wipe the old `features.parquet` still lists creators that no longer exist. Rerun the pipeline, or delete the files in `backend/data/` first. Until then the leaderboard shows the old creators and `/recommend` answers 404 for them.

The generator is not idempotent. Running it a second time against the same database adds another full set of creators.

## Running without Docker

Docker is the supported route. The following works if you need a native setup. It was exercised in a scratch environment (Python 3.13, PostgreSQL 16 with pgvector, real Postgres, embeddings stubbed) but is not part of the project's CI.

1. Install PostgreSQL 16 with the pgvector extension available. Create a database and user.
2. Create a Python 3.11 virtual environment in `backend/` and install `requirements.txt` and `requirements-ml.txt`. The second file pulls PyTorch from the CPU index.
3. Export the five required variables (or create `backend/.env`) with a `DATABASE_URL` pointing at your database, for example `postgresql://user:password@localhost:5432/contentiq`.
4. From `backend/`: `alembic upgrade head`, then `uvicorn app.main:app --port 8000`.
5. Run the scripts from `backend/` as `python scripts/<name>.py`. `train_model.py` also needs an MLflow server and `MLFLOW_TRACKING_URI` set to it. A `file:` URI also works for a local store.
6. Frontend: `cd frontend && npm ci && npm run dev`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| API container exits with `ValidationError ... Field required` | A required variable is missing from the root `.env` | Compare with `.env.example`. |
| API exits with `ValueError: LLM_PROVIDER must be one of ('mock', 'gemini')` | Typo in `LLM_PROVIDER` | Fix the value in `.env` and recreate the API container |
| API exits with `ValueError: GEMINI_API_KEY is not set` | `LLM_PROVIDER=gemini` with an empty key | Set the key, or set `LLM_PROVIDER=mock`. |
| `503 Feature table not found at ... Run scripts/build_features.py first.` | `backend/data/features.parquet` does not exist | Run the pipeline from step 5 of the README. |
| `503 Classifier not found at ... Run scripts/train_model.py first.` | No trained model. `/recommend` checks for it before it calls the LLM. | Run `train_model.py`. |
| `404 No content found for user_id ...` | The ID is mistyped, is not a UUID, or is not in the feature table (creator ingested after the last `build_features.py`, or no posts with usable metrics) | Check the ID, then rebuild features. |
| `404 User ... has no top-performing content yet ...` | The creator has no post labeled as an over-performer | Pick a creator with more history. |
| `404 No user found with id ...` on `/recommend` or `/recommendations` | The creator is in `features.parquet` but not in PostgreSQL, usually after `down -v` | Rerun the pipeline. |
| `502 Failed to generate any valid candidates ...` | All three candidates failed. The inner messages name the cause, for example `Gemini API call failed or was blocked: ...` (bad key or model, quota, network, timeout) or schema validation errors. | Fix the Gemini settings or switch to the mock. Nothing is saved on failure. |
| Frontend says "Backend data isn't built yet" | The API returned 503 | Run the pipeline. |
| Frontend says "Couldn't reach the server." | API down, wrong `NEXT_PUBLIC_API_BASE_URL`, or a CORS block | Check `http://localhost:8000/health`. The API allows only the origin `http://localhost:3000`. Opening the app at `http://127.0.0.1:3000` or another port is blocked by CORS. |
| Compose cannot bind the database port | Something else uses the port | Change `POSTGRES_PORT`. For ports 3000, 8000 or 5001, edit the mappings in `docker-compose.yml`. |
| `alembic` errors after `down -v` | Fresh database with no schema | Run `alembic upgrade head`. |
| `vitest: not found` when running `npm test` on the host | `node_modules` not installed on the host | `cd frontend && npm ci`, or run the tests in the container. |
| `npm run build` fails fetching fonts | `next/font/google` downloads Inter at build time | Build with internet access. |
| The first `/recommend` or `/predict` after a restart is slow | The embedding model is loaded on first use | Expected. Later calls reuse it. |
| Backend tests wrote to your database | The suite uses the database in `DATABASE_URL`. It deletes the users it created when it finishes, but not if the run is killed. | See [development.md](development.md#testing). |
