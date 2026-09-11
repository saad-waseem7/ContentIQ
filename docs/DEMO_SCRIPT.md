# ContentIQ — Demo Script (10–15 min)

## Setup (before the audience arrives)

```bash
docker compose up -d
docker compose ps
```
Confirm `db`, `api`, `mlflow`, `frontend` all show `Up`/`healthy`.

Get a real user ID to demo with:
```bash
docker exec -it contentiq_db psql -U contentiq -d contentiq -c "\pset pager off" -c "SELECT id, niche FROM users LIMIT 5;"
```

Open `http://localhost:3000`.

**Fallback if Gemini is unavailable or rate-limited during the demo:** set `LLM_PROVIDER=mock` in `backend/.env`, then `docker compose up -d --force-recreate api`. The recommendation flow still works fully with deterministic mock output — every other part of the demo (leaderboard, insights, predict, scoring) is unaffected either way, since only idea *generation* is mocked, not scoring.

## 1. Leaderboard (2 min)
Paste a real `user_id`. Point out: ranked by performance relative to *this creator's own* baseline, not a generic average — the top post is the exact planted signal used to prove the model recovers real structure, not noise.

## 2. Insights (3 min)
Switch tabs. Walk through the personal pattern cards, the performance-by-topic and trend charts, "you vs. your niche," and topic clusters. Point out: fully deterministic, no LLM narration — every number is directly computed with sample-size gating so thin evidence is never shown as a strong conclusion.

## 3. Daily Recommendation (4 min)
Click **Generate**. While it loads: "This makes up to 3 real Gemini calls — one safe/proven angle, one alternative framing, one experimental-but-grounded angle — then scores all three with the same trained classifier and keeps the winner." Point out the rationale citing a real number and the predicted score. Click **Mark actioned**; generate again and click **Dismiss**.

## 4. Try Your Own Idea (2 min)
Scroll to the panel on the same page. Submit a made-up idea, show the real predicted score. Point out: identical scoring path as the daily recommendation, just skipping generation.

## 5. Dark mode + responsiveness (1 min)
Toggle the theme, note it persists on reload. Narrow the window briefly.

## 6. Under the hood, if time allows (2–3 min)
- MLflow UI (`localhost:5001`) — a training run, SHAP artifact.
- `docs/KNOWN_LIMITATIONS.md` — what's known to be unfinished and why.