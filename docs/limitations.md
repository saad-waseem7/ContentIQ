# Limitations, security considerations and deferred work

This is the honest list. Items were found by reading the code and, where noted, by running it during the handover review. Nothing here has been fixed, because the handover scope excluded code changes. Read it before you reuse any part of the project.

How to read the labels: **verified** means observed in the code or reproduced by running it. **Not verified** means stated from reading code or from the project owner and not exercised.

## Scope and data

- **Synthetic data only.** All creators, posts and metrics come from `synthetic_data/generator.py` with a planted signal. Model metrics measure recovery of that signal, not performance on real creators. See [ml-pipeline.md](ml-pipeline.md).
- **No platform connectors.** No OAuth, no scraping, no scheduled sync. Data enters through `POST /ingest`.
- **Reach-based engagement rate.** `performance_raw` divides interactions by `reach` from the latest metric snapshot. Posts without usable reach are dropped. Views, watch time, follower growth and impressions are stored but do not enter the metric.
- **Niche is free text on ingest, but the model knows five.** A new niche works for the leaderboard and insights but is unknown to the classifier.
- **UTC only.** `posting_hour` and posting windows are UTC. There is no per-creator timezone.
- **One snapshot per post.** Only the latest metric snapshot is used, so a post's rate depends on when its last snapshot was taken.

## Security considerations

The project has no security model beyond input validation. Do not expose it to an untrusted network as it stands.

| Issue | Detail |
| --- | --- |
| No authentication or authorization | Every endpoint is open. Anyone who can reach the API can read any creator's leaderboard, insights and recommendations by guessing or enumerating IDs, change a recommendation's status by ID, and call `/ingest`. |
| Unauthenticated writes | `POST /ingest` creates users, channels, content and metrics for anyone. Bulk posting can fill the database. |
| Cost abuse | `POST /recommend` makes up to 6 Gemini calls per request with no rate limit or quota. A loop of requests spends your key's quota or budget. |
| Prompt injection surface | `niche`, topic tags and captions that reach the prompt come from ingested data. Attacker-controlled text can try to steer the model. Output is validated against closed lists and a numeric grounding check, which limits the damage, but the caption and rationale text are free-form and shown to users. |
| Pickle deserialization | `classifier.joblib` is loaded with `joblib.load`. A tampered file runs code in the API process. Treat `backend/data/` as trusted, and never load a model from an unknown source. |
| Default credentials and exposed port | `.env.example` is meant to be edited, but the database port is published on the host, and a weak password makes it reachable from other machines on the network. |
| CORS | Allows `http://localhost:3000` only, hard-coded in `app/main.py`. Deploying anywhere else requires a code change. |
| Development servers | Compose runs `uvicorn --reload` and `next dev`. They are not hardened, and `./backend` and `./frontend` are bind-mounted into the containers. |
| Secrets in images | There is no `.dockerignore`. `COPY . .` copies a local `backend/.env` and `backend/.venv` into the API image, and the frontend image copies `frontend/.env.local`. An image built on a machine that holds real keys contains them. |
| No TLS, no security headers, no request-size limits beyond field limits | Not configured. |
| Per-process caches and a shared model | Safe with the single-process compose setup. Multi-worker behavior and heavy concurrent use were not tested. |

Before sharing a ZIP or a repository, check that `.env`, `backend/.env` and `frontend/.env.local` are not included. The ZIP supplied for this handover contained real `.env` files. They were not read or copied into the documentation, but if the project has been shared in that form, rotate any key that was in them.

## Defects and rough edges

All **verified** by code reading unless stated.

### API behavior

- **Duplicate content ID returns 500.** `POST /ingest` inserts content without checking for an existing ID and the database integrity error is not handled.
- **`/ingest` is create or return, not upsert.** A repeated user or channel ID returns the existing row and silently ignores the other submitted fields.
- **Missing model returns 503 only after the LLM calls.** In `/recommend`, scoring happens after generation, so with no trained model you pay for the calls and then get a 503.
- **`/predict` accepts negative `duration_sec`** and any integer. Metric counts and follower counts on `/ingest` also have no range checks.
- **No platform and format compatibility check.** `/recommend` can propose a format the creator's platform does not support.
- **`/health` fails with a 500 when the database is down** instead of reporting a degraded status.
- **Unknown IDs and malformed IDs both give 404** (not 422) on most endpoints.
- **Typos in `LLM_PROVIDER` silently select the mock.** Only the exact value `gemini` selects Gemini.

### Recommendations and scoring

- **`days_since_last_post` uses the wall clock.** Predicted scores drift as the real date moves away from the synthetic dataset. Measured shift on the shipped data: mean 0.053, maximum 0.148. Posting hour and weekday are frozen to the creator's winner mode, so this is the only time-dependent input.
- **Feedback is not used.** `actioned` and `dismissed` are stored and never read by the generation, grounding or training code.
- **Only the winning candidate is stored.** The other two cannot be recovered.
- **The topic only helps if the model knows it.** A new topic is scored as missing.
- **Scores are not calibrated.** Treat them as a ranking signal. The 40 and 70 percent badge cut-offs in the UI are arbitrary.
- **Rationale checking is numeric only.** A rationale with correct numbers can still say something unsupported.
- **`linked_content_id` is never set.** The column exists on `recommendations`. No code writes it, so a recommendation is never linked to the post that later implements it.

### Leaderboard and Insights

- **Threshold mismatch.** Insights use posts with at least 3 earlier posts. The Leaderboard ranks posts with at least 10. Counts differ between the two screens for the same creator by design, but it is easy to read as an inconsistency.
- **Insights are descriptive averages** over small groups with no significance testing.
- **Trend is baseline-relative.** A steadily improving creator can appear stable. See [insights-and-leaderboard.md](insights-and-leaderboard.md#trend).
- **Cluster labels are majority values**, not semantic names.

### Data pipeline

- **Manual refresh.** The feature table and model are rebuilt by running scripts by hand. There is no schedule, trigger or staleness check. New data is invisible until `build_features.py`, and the model does not learn it until `train_model.py`.
- **`train_model.py` overwrites the serving files before it evaluates.** A failure afterwards (MLflow down, a SHAP error) leaves a new, unevaluated model in place. The pass and fail lines it prints do not roll anything back.
- **Mismatched model files.** `classifier.joblib` and `category_levels.json` must come from the same run. Nothing verifies that.
- **Stale `backend/data/` after a database wipe.** The files outlive `docker compose down -v` because they live on the host. The API then lists creators that no longer exist.
- **The generator is not idempotent** and sends one HTTP request per post.
- **`user_baselines` is unused.** `compute_baselines.py` fills it, and no application code reads it. It is a leftover of the original design.
- **`synthetic_data/validate.sql` check 7 understates the planted effect.** It compares Tuesday and Thursday 19:00 to 20:59 against everything else, while the generator boosts Monday to Friday 17:00 to 20:59. Treat that check as indicative only. See [ml-pipeline.md](ml-pipeline.md).
- **The regressor is trained and tracked, but unused.** Its per-creator Spearman correlation (0.3441 in the reproduced run) is below the 0.40 acceptance threshold.

### Testing and repository hygiene

- **The backend suite writes to the configured database** and leaves rows behind. The shipped dataset holds 28 such test users. See [development.md](development.md#testing).
- **One backend test is flaky** under threading (see development.md). It passed in the owner's Docker run.
- **The tracked example files are traps.** `backend/.env.example` (port 5433, Gemini selected, placeholder key) and `frontend/.env.local.example` (placeholder URLs) break the Docker setup if copied unchanged. See [setup.md](setup.md#using-the-example-files-safely).
- **No linter, formatter, type checker or pre-commit hooks.**
- **No `.dockerignore`.**
- **`temp.txt` in the repository root** is a scratch file with ad hoc SQL. It is gitignored. Do not rely on it.
- **Local clutter.** Archives of this repository can contain `backend/.venv`, `frontend/node_modules`, `.next`, `.pytest_cache` and `backend/data`. All are gitignored or regenerable. Do not package them.

### LLM provider

- **Gemini model name is not verifiable here.** The default `GEMINI_MODEL` is `gemini-3.6-flash`. Whether your key can call that name was not checked, because the review environment had no outbound access to Google. The owner ran the live Gemini path once manually. Set `GEMINI_MODEL` explicitly.
- **Free-tier quota is small** (about 20 requests a day was observed by the maintainers). Not verified against current Google terms.
- **Stall bound.** Per call timeout and disabled SDK retries bound a stalled provider to about two timeouts per request. This was tested with a fake model and the error path, not with a real stalled connection.

## Deferred work

Items in the original product requirements document, or implied by the code, that are not built.

| Item | State |
| --- | --- |
| Authentication, tenancy, per-user access control | Not built |
| Real platform connectors and OAuth | Not built |
| Scheduled retraining, nightly baselines, automatic feature refresh | Not built, scripts are manual |
| Feedback loop from `actioned` and `dismissed` into training or prompts | Not built |
| Vector similarity retrieval with pgvector | Not built. Vectors are stored, never queried in SQL. |
| `/stats` endpoint | Not built |
| Regressor at the 0.40 Spearman target | Trained, below target, not served |
| Per-creator timezones | Not built |
| Production deployment (non-dev servers, TLS, secrets management, monitoring) | Not built |
| Pagination | Not built |
| Support for niches outside the five synthetic ones in the model | Not built |

## What was not verified for this documentation

- Docker Compose was not run. The commands in the README follow `docker-compose.yml`, the Dockerfiles and the scripts. They were checked by reading and not executed in containers.
- The 125-user dataset was not regenerated. Model metrics in [ml-pipeline.md](ml-pipeline.md) were reproduced by running the training code on the supplied `features.parquet`.
- A native smoke test (PostgreSQL 16 with pgvector, migrations, a small generated dataset, scripts, API, mock LLM) was run in a scratch environment with the embedding model stubbed. The frontend suite passed there. The backend suite had 155 passing and 1 flaky failure.
- Real Gemini calls, the real embedding model under load, browser rendering of the frontend, and the GitHub Actions workflow were not exercised.
