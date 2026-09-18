# ContentIQ Demo Script (10–15 min)

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

**Fallback if Gemini is unavailable or rate-limited during the demo:** set `LLM_PROVIDER=mock` in `backend/.env`, then run `docker compose up -d --force-recreate api`. The recommendation flow still works with deterministic mock output. The leaderboard, insights, predict, and scoring flows are unchanged because only idea generation is mocked.

## 1. Leaderboard (2 min)
Paste a real `user_id`. Point out that posts are ranked against this creator's own baseline, not a generic average. The top post reflects the planted signal used to test whether the model recovers real structure rather than noise.

## 2. Insights (3 min)
Switch to Insights and walk through the personal pattern cards, performance by topic, trend charts, "you vs. your niche," and topic clusters. Point out that these results are deterministic and do not use LLM narration. Each number is computed from the data, with sample-size checks to avoid presenting thin evidence as a strong conclusion.

## 3. Daily Recommendation (4 min)
Click **Generate**. While it loads, explain that the system makes up to three Gemini calls concurrently: one safe or proven angle, one alternative framing, and one experimental but grounded angle. It scores all three with the same trained classifier and keeps the winner. Point out the rationale, the real number it cites, and the predicted score.

Use the active recommendation controls to mark the result **Actioned**, then generate another recommendation and mark it **Dismissed**. The active recommendation remains visible until it is cleared or replaced.

## 4. Recommendation History (1 min)
Open **History** and show that both recommendations appear newest first with their predicted scores and statuses. Point out that feedback is retained, while older recommendations remain an accurate record of what was generated at the time.

## 5. Try Your Own Idea (2 min)
Open **Predict** and submit a made-up idea. Show the predicted score and explain that it uses the same feature and scoring path as a daily recommendation, but skips idea generation and does not save the result.

## 6. Dark mode and responsiveness (1 min)
Toggle the theme and reload to show that the preference persists. Narrow the window briefly to show the responsive layout.

## 7. Under the hood, if time allows (2–3 min)
- MLflow at `localhost:5001`: show a training run and a SHAP artifact.
- Swagger at `localhost:8000/docs`: show the main API endpoints, including recommendation history and feedback.
- `docs/KNOWN_LIMITATIONS.md`: explain what remains unfinished and why.