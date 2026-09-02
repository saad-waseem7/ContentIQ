# ContentIQ — Demo Script (10–15 min)

## 1. Setup check (30s)
`docker compose ps` — confirm `db`, `api`, `mlflow`, `frontend` all `Up`/`healthy`.
Open `http://localhost:3000`.

## 2. Leaderboard (2 min)
Navigate to **Leaderboard**. Paste a real `user_id` (query `SELECT id, niche FROM users LIMIT 5;` if needed).
Talking point: "Every post ranked by performance relative to *this creator's own* baseline — not a generic average. The top post here is the exact signal we planted in the synthetic dataset to prove the model can recover real structure."

## 3. Insights (3 min)
Switch to **Insights**. Walk through: personal pattern cards (top content type/time/topic/hook), the performance-by-topic and trend charts, "you vs. your niche," and topic clusters.
Talking point: "All deterministic, no LLM narration — every number is directly computed from real historical data, with sample-size gating so thin evidence never gets presented as a strong conclusion."

## 4. Daily Recommendation (4 min)
Switch to **Daily recommendation**, click **Generate**.
Talking point while it loads: "This makes up to 3 real Gemini calls — one safe/proven angle, one alternative framing, one experimental-but-grounded angle — then scores all three with the same trained classifier and shows the winner."
Once loaded: point out the rationale citing a real number, the predicted score. Click **Mark actioned**, then generate again and click **Dismiss**.

## 5. Try Your Own Idea (2 min)
Scroll down on the same page to the **Try your own idea** panel. Submit a made-up idea, show the real predicted score.
Talking point: "Same trained model, same scoring path as the daily recommendation — just skipping generation and using a user-submitted idea instead."

## 6. Dark mode + responsiveness (1 min)
Toggle the theme control, note persistence across reload. Narrow the browser to mobile width briefly.

## 7. Under the hood, if time allows (2–3 min)
- MLflow UI (`localhost:5001`) — show a training run, SHAP artifact.
- `docs/KNOWN_LIMITATIONS.md` — "here's what we know isn't finished, and why we chose not to build it yet."