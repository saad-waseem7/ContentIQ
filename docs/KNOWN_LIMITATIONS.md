# Known Limitations

Consolidated from decisions made and disclosed throughout development. Each is a deliberate scope choice, not an oversight.

## Regressor Spearman correlation (0.32–0.36 vs. 0.40 target)
Diagnosed as structural: most of the synthetic label's variance is Pareto noise by design, not a learnable pattern. Five tuning attempts (loss function, regularization, learning rate, an engineered feature) and a full PCA-on-embeddings experiment were tried; none closed the gap, and PCA measurably regressed both headline metrics and was reverted. The classifier (used for all real scoring in `/recommend` and `/predict`) is unaffected — it uses a separate model and clears its own target cleanly.

## Batch feature/model artifacts (`features.parquet`, `classifier.joblib`, etc.)
Rebuilt by manual script runs, not live-updated. Acceptable at the current scale with no continuous real ingestion; would need addressing before any real, continuously-ingesting deployment.

## No authentication — every `user_id`/`recommendation_id` is caller-supplied
Every endpoint trusts the caller's identity claim. This is a real, live IDOR — anyone who knows or guesses a UUID can read another user's data or trigger a real (cost-incurring) Gemini call on their behalf. Deferred per the PRD's "auth stubbed for MVP," but this framing was written before the product made real external API calls — worth an explicit decision before any non-local/shared deployment.

## Gemini free-tier rate limits
20 requests/day on the free tier, confirmed by hitting it directly during evaluation. A single recommendation can use up to 6 calls (3 candidates × up to 2 attempts each). Fine for local demo use; a real constraint for any broader usage.

## Frontend tests use mocked API responses, not full end-to-end
Component/interaction tests (leaderboard, recommend, insights, predict, theme, user context) are real and assert genuine behavior, but against a mocked `fetch`, not a live backend. A real backend contract change wouldn't be caught by this suite alone — only by manual verification.

## Deliberately deferred, not attempted
- **pgvector-based grounding retrieval** — current grounding (rank by `performance_z`) already satisfies the functional intent; no query-vector formulation was found to offer a genuine improvement over it.
- **Real platform connectors / OAuth** — no real creator data exists yet to connect to.
- **Week 8 self-optimization** (nightly jobs, retraining, feedback-driven re-ranking) — blocked on real feedback volume, not effort; confirmed via direct query that accumulated feedback remains too thin for anything beyond fitting to noise.
- **`/stats` endpoint** — maps to an MVP-deferred channel-overview screen with no current frontend consumer.