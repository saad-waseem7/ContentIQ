# ContentIQ — Final Project Status

## Purpose
A personalized content performance coach: models each creator's post performance against their own historical baseline, then uses that model to generate, rank, and score new content recommendations grounded in real evidence.

## What was implemented
- Docker Compose environment: PostgreSQL + pgvector, FastAPI, MLflow, Next.js frontend.
- Alembic-managed schema (3 migrations), CI on every push.
- Synthetic dataset generator: 5 niches, 125 users, ~21.5k posts, deliberately planted hidden signal.
- Leakage-safe feature pipeline (expanding-window, test-enforced), sentence-transformer embeddings, per-user/platform/content-type baselines.
- LightGBM classifier + regressor, SHAP interpretability, MLflow-tracked training.
- Content Performance Leaderboard.
- Insight Engine: personal pattern breakdowns, non-causal trend detection, niche comparison, niche-scoped topic clustering.
- LLM recommendation engine (Google Gemini, provider-agnostic interface): 3 strategically-diverse candidates per request, each scored by the trained classifier, highest-scoring candidate returned with a grounded rationale.
- Standalone `/predict` endpoint reusing the same scoring path.
- Actioned/Dismissed feedback capture.
- Full frontend: Leaderboard, Insights, Daily Recommendation, Predict, dark mode.

## Technical components
FastAPI · SQLAlchemy · Alembic · PostgreSQL 16 + pgvector · LightGBM · scikit-learn · SHAP · sentence-transformers · MLflow · Google Gemini · Next.js 14 · TypeScript · Tailwind CSS · Recharts · pytest · Vitest/RTL · GitHub Actions · Docker Compose.

## Validation performed
- Full pipeline (generate → embed → build features → train) reproduced successfully from a clean, migrated database on three separate environments (Windows, Fedora, Ubuntu) during this project.
- Backend test suite: 71 tests passing.
- Frontend test suite: 16 tests passing.
- All four user-facing flows (Leaderboard, Insights, Daily Recommendation with real Gemini calls and feedback, Predict) manually verified end-to-end with real data.
- CI runs the backend suite automatically against a clean database on every push.

## Model results
| Metric | Result | Target |
|---|---|---|
| Classifier ROC-AUC | ~0.74–0.75 | ≥ 0.70 — met |
| Classifier vs. baseline | beats content-type-average | met |
| Regressor Spearman ρ | ~0.32–0.36 | ≥ 0.40 — not met, documented |
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

## Known limitations
See `docs/KNOWN_LIMITATIONS.md` for the full list: regressor Spearman shortfall, synthetic-only data, batch artifact staleness, no authentication (live IDOR), Gemini rate limits, mocked-API-only frontend test coverage, and two environment/configuration gotchas discovered during multi-machine setup.

## Deferred scope
Production authentication, real platform connectors/OAuth, Week 8 self-optimization (blocked on real feedback volume), `/stats`, pgvector-based retrieval, further regressor tuning. Each was evaluated on its own merits, not skipped by default — see `docs/KNOWN_LIMITATIONS.md` for the specific reasoning behind each.

## Closure decision
**READY TO CLOSE.** Core functionality is complete, demonstrable, and tested across three independent environments. No blocking defect remains. Known limitations are understood, documented, and appropriately scoped for a 4-week internship MVP rather than a production system.