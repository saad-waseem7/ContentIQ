# ContentIQ Final Project Status

## Purpose
A personalized content performance coach that models each creator's post performance against their own historical baseline, then uses that model to generate, rank, and score recommendations grounded in real evidence.

## What was implemented
- Docker Compose environment: PostgreSQL + pgvector, FastAPI, MLflow, Next.js frontend.
- Alembic-managed schema (3 migrations), CI on every push.
- Synthetic dataset generator: 5 niches, 125 users, ~21.5k posts, deliberately planted hidden signal.
- Leakage-safe feature pipeline (expanding-window, test-enforced), sentence-transformer embeddings, per-user/platform/content-type baselines.
- LightGBM classifier + regressor, SHAP interpretability, MLflow-tracked training.
- Content Performance Leaderboard.
- Insight Engine: personal pattern breakdowns, non-causal trend detection, niche comparison, niche-scoped topic clustering.
- LLM recommendation engine (Google Gemini, provider-agnostic interface): three strategically diverse candidates generated concurrently per request, each scored by the trained classifier, with the highest-scoring candidate returned alongside a grounded rationale.
- Standalone `/predict` endpoint reusing the same scoring path.
- Actioned/Dismissed feedback capture.
- Recommendation History: view a user's previously generated recommendations, newest first, including their statuses and predicted scores.
- Full frontend: Leaderboard, Insights, Daily Recommendation with a persistent active recommendation and Clear control, History, Predict, and dark mode.

## Technical components
FastAPI · SQLAlchemy · Alembic · PostgreSQL 16 + pgvector · LightGBM · scikit-learn · SHAP · sentence-transformers · MLflow · Google Gemini · Next.js 14 · TypeScript · Tailwind CSS · Recharts · pytest · Vitest/RTL · GitHub Actions · Docker Compose.

## Validation performed
- Full pipeline (generate, embed, build features, and train) reproduced successfully from a clean, migrated database on three separate environments: Windows, Fedora, and Ubuntu.
- Backend test suite: 71 tests passing.
- Frontend test suite: 16 tests passing.
- The main user-facing flows, including Leaderboard, Insights, Daily Recommendation with Gemini and feedback, Predict, and History, were manually verified end to end with real data.
- CI runs the backend suite automatically against a clean database on every push.

## Model results
| Metric | Result | Target |
|---|---|---|
| Classifier ROC-AUC | ~0.74–0.75 | ≥ 0.70, met |
| Classifier vs. baseline | beats content-type-average | met |
| Regressor Spearman ρ | ~0.32–0.36 | ≥ 0.40, not met and documented |
| Planted signal recovery (SHAP) | confirmed, all 5 niches | met |

## Recommendation evaluation results
A real evaluation against live Gemini output found the original single-prompt, 3-candidate design produced near-duplicate ideas. After introducing three distinct strategic directives per candidate, a repeat evaluation showed:

| Metric | Before | After |
|---|---|---|
| Identical hook_type across all 3 candidates | 100% | 0% |
| Identical topic across all 3 candidates | 100% | 0% |
| Identical content_type across all 3 candidates | 88% | 40% |
| Average classifier score spread | 0.076 | 0.295 |
| Winner matches a standout personal pattern | 88% | 100% |

## Posting-time scoring fix
A separate investigation found that identical ideas could receive scores from 44% to 91% based only on the wall-clock moment of generation. The model's most influential posting-time features, `posting_hour` and `posting_day_of_week`, were previously derived from `datetime.now()`. The fix anchors them to the mode of the user's historically best-performing posting times instead.

After the fix, the same sensitivity sweep produced a flat score across all 24 sampled hours. Historical recommendations generated before the fix remain visible in Recommendation History as an accurate record, but may contain scores affected by the old behavior.

## Known limitations
See `docs/KNOWN_LIMITATIONS.md` for the full list: regressor Spearman shortfall, synthetic-only data, batch artifact staleness, no authentication (live IDOR), Gemini rate limits, mocked-API-only frontend test coverage, and two environment/configuration gotchas discovered during multi-machine setup.

## Deferred scope
Production authentication, real platform connectors and OAuth, Week 8 self-optimization (blocked on real feedback volume), `/stats`, pgvector-based retrieval, and further regressor tuning. Each was evaluated on its own merits. See `docs/KNOWN_LIMITATIONS.md` for the reasoning behind each decision.

## Closure decision
**READY TO CLOSE.** Core functionality is complete, demonstrable, and tested across three independent environments. No blocking defect remains. Known limitations are understood, documented, and appropriately scoped for a 4-week internship MVP rather than a production system.