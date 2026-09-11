# Known Limitations

Each of these is a deliberate scope decision, verified and reasoned about during development — not an oversight.

## Regressor Spearman correlation (~0.32–0.36 vs. 0.40 target)
Diagnosed as structural: most of the synthetic label's variance is noise by design, not a learnable pattern. Five tuning attempts and a full PCA-on-embeddings experiment (implemented, measured, found to regress both metrics, reverted) did not close the gap. Not used for any live scoring — `/recommend` and `/predict` both use the classifier only, which clears its own target.

## Synthetic data, not real production data
The entire dataset (125 users, 5 niches, ~21.5k posts) is generated with a deliberately planted, SHAP-verified hidden signal. No real creator data or real platform connector exists yet.

## Batch feature/model artifacts
`features.parquet`, `classifier.joblib`, etc. are rebuilt by manual script runs, not live-updated. Acceptable with no continuous real ingestion; would need addressing before any deployment with ongoing real data.

## No authentication — every `user_id` / `recommendation_id` is caller-supplied
A real, live IDOR: anyone who knows or guesses a UUID can read another user's data or trigger a real Gemini call on their behalf. Deferred as MVP-stubbed auth, but this project now makes real, cost-incurring external API calls — worth an explicit decision before any shared or non-local deployment.

## Gemini free-tier rate limits
20 requests/day observed in practice. A single recommendation can use up to 6 calls (3 candidates × up to 2 attempts each). Fine for local demo use.

## Frontend tests use mocked API responses
Component/interaction tests are real and assert genuine behavior, but against a mocked `fetch`, not a live backend. A real backend contract change would only be caught by manual verification, not this suite alone.

## Two separate `.env` files must each be complete
`ContentIQ/.env` (read by Docker Compose) and `backend/.env` (read directly by the Python app) do not share values automatically. Adding a setting to one without the other's required fields present causes the API to fail on startup with a `pydantic` validation error. Discovered directly during a cross-environment setup.

## `docker compose down -v` wipes the database
Migrations must be rerun (`alembic upgrade head`) afterward. Skipping this causes confusing, seemingly-unrelated failures in every downstream service (frontend errors that look like CORS/connectivity issues are often actually this).

## Deliberately deferred, not attempted
- **pgvector-based grounding retrieval** — current grounding (rank by performance score) already satisfies the functional intent; no query-vector formulation was found to offer a genuine improvement.
- **Real platform connectors / OAuth** — no real creator data exists yet to connect to.
- **Week 8 self-optimization** (nightly jobs, retraining, feedback-driven re-ranking) — blocked on real feedback volume, confirmed too thin via direct query.
- **`/stats` endpoint** — maps to a screen with no current frontend consumer.