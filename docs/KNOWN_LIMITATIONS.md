# Known Limitations

These are deliberate scope decisions that were identified and documented during development.

## Regressor Spearman correlation (approximately 0.32 to 0.36 vs. 0.40 target)
This appears to be structural. Most of the synthetic label's variance is noise by design rather than a learnable pattern. Five tuning attempts and a full PCA-on-embeddings experiment did not close the gap, and the PCA experiment reduced both headline metrics. The regressor is not used for live scoring. Both `/recommend` and `/predict` use the classifier, which clears its own target.

## Synthetic data, not real production data
The entire dataset (125 users, 5 niches, ~21.5k posts) is generated with a deliberately planted, SHAP-verified hidden signal. No real creator data or real platform connector exists yet.

## Batch feature/model artifacts
`features.parquet`, `classifier.joblib`, etc. are rebuilt by manual script runs, not live-updated. Acceptable with no continuous real ingestion; would need addressing before any deployment with ongoing real data.

## No authentication: every `user_id` and `recommendation_id` is caller-supplied
Anyone who knows or guesses a UUID can read another user's data or trigger a Gemini call on their behalf. Authentication was deferred for this MVP, but the risk matters before any shared or non-local deployment because Gemini calls can incur real cost.

## Gemini free-tier rate limits
Around 20 requests per day were observed in practice. A single recommendation can use up to six calls, since each of the three candidates may be retried once. This is fine for local demo use.

## Frontend tests use mocked API responses
Component and interaction tests assert real frontend behavior, but they use a mocked `fetch` rather than a live backend. A backend contract change would therefore require manual verification or an additional integration test.

## Two separate `.env` files must each be complete
`ContentIQ/.env` is read by Docker Compose and `backend/.env` is read directly by the Python app. They do not share values automatically. Adding a setting to one file without the required fields in the other can cause the API to fail at startup with a Pydantic validation error.

## `docker compose down -v` wipes the database
Migrations must be rerun with `alembic upgrade head` afterward. Skipping this can cause confusing failures in downstream services. Frontend errors that look like CORS or connectivity issues may actually be caused by the empty database.

## Deliberately deferred work
- **pgvector-based grounding retrieval:** current grounding, which ranks by performance score, satisfies the functional goal. A query-vector approach was not found to provide a clear improvement.
- **Real platform connectors and OAuth:** no real creator data exists yet to connect to.
- **Week 8 self-optimization:** nightly jobs, retraining, and feedback-driven re-ranking are blocked by the limited amount of real feedback available.
- **`/stats` endpoint:** it maps to a screen with no current frontend consumer.

## Historical recommendation scores predate the posting-time fix
Recommendations generated before the posting-time fix, described in `FINAL_PROJECT_STATUS.md`, used the wall-clock time of generation rather than the user's historically best-performing posting time. A controlled sensitivity test found that the same idea for the same user could receive scores from 44% to 91% based on generation time alone.

These historical rows remain visible in Recommendation History as an accurate record of what was generated and when. They were not re-scored retroactively because that would change the historical record. Recommendations generated after the fix use the corrected, stable scoring logic.