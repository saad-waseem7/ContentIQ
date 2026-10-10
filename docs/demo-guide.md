# Demo guide

A walkthrough for presenting ContentIQ in about 10 minutes, with a preparation checklist and the points where a demo can go wrong. It assumes the setup in the [README](../README.md) is complete. Example values are not given on purpose: your generated data and trained model will produce different numbers, and the demo should use what is on your screen.

## Before the demo

Run these from the repository root on the host. Each one should succeed before you present.

```bash
docker compose ps                                  # db, api, mlflow, frontend are running
curl -s http://localhost:8000/health               # {"status":"ok","database":"connected"}
ls backend/data                                    # features.parquet, classifier.joblib, category_levels.json
```

1. **Choose a creator in advance.** The leaderboard needs at least 10 earlier posts in a platform and format group before a post is ranked, so pick a creator with a long history in one platform. The query in README step 6 lists creators by post count. Check the choice against the API before the demo:

   ```bash
   curl -s "http://localhost:8000/content?user_id=PASTE_ID_HERE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['niche'], d['ranked_posts'], 'ranked of', d['total_posts_in_history'])"
   ```

   Use a creator with a healthy `ranked_posts` count. Creators with spread-out formats can have short lists.
2. **Warm the caches.** Open Insights and generate one recommendation once before presenting. The first Insights request for a niche fits KMeans, and the first recommendation or custom score after an API restart loads the embedding model. Both are slow once and fast afterwards.
3. **Copy the user ID to your clipboard.** Paste it into the "Viewing user" box. Do not type it (see below).
4. **Decide on the LLM.** The mock client is deterministic and free: all three candidates are identical, so the "three candidates, best one saved" story is visible only in how it is built, not in the output. Gemini gives real variety but needs a key, network access and quota (the free tier is small; a recommendation uses up to 6 calls). Test Gemini once before an audience and keep `LLM_PROVIDER=mock` as the fallback. Switching needs `docker compose up -d --force-recreate api`.
5. **Open the pages in one browser tab** at `http://localhost:3000`. The API only allows that exact origin, so `127.0.0.1:3000` fails with a CORS error.
6. **Keep these tabs ready:** Swagger UI at `http://localhost:8000/docs`, and MLflow at `http://localhost:5001` if you will show the training run.

## Walkthrough

### 1. Frame the problem (1 minute)

Creator dashboards show absolute numbers, so a creator with 500 followers always looks bad next to one with 500,000. ContentIQ judges every post against the same creator's own earlier posts on the same platform and format. State the limits early: the data is synthetic and there is no real platform connection.

### 2. Leaderboard (2 minutes)

Paste the user ID, open **Leaderboard**.

- Point at the header line, "N ranked of M total posts". Not every post is ranked, because a post needs at least 10 earlier posts in its group to have a trustworthy baseline.
- Each row shows the format, platform, hook, topics, date and a performance badge with the z-score: how many standard deviations above or below this creator's own earlier average for that format and platform. The badge reads Strong above 1, Below Average below -0.5 and Average otherwise.
- The raw engagement rate and the top-performer flag are in the API response (`performance_raw`, `is_top_performer`) but are not shown in the table. Open `/docs` or the `curl` output to show them if you want to make the point that a high rank does not mean the highest raw rate.

### 3. Insights (3 minutes)

Open **Insights** and walk the sections top to bottom. Details are in [insights-and-leaderboard.md](insights-and-leaderboard.md).

- **Personal patterns:** which hooks, topics and posting windows had a mean z above 0.5, with their sample counts. Say that each needs at least 5 posts and that these are averages, not causes. Posting windows are in UTC.
- **Trend:** last 60 days against the earlier period. Mention it is descriptive. A creator who keeps improving can look flat because the baseline moves with them.
- **Monthly chart:** months with at least 3 posts.
- **Niche comparison:** engagement ratio against other creators of the same platform and format. If it says there is not enough data, that is the thresholds working (10 other creators, 50 posts).
- **Niche patterns and topic clusters:** niche-wide hooks and topics, and KMeans clusters on caption embeddings. The cluster names are the most common hook, format and topic among members, not generated labels.

### 4. Daily Recommendation (3 minutes)

Open **Daily Recommendation** and click **Generate Recommendation**.

- The creator's top posts are fed to the LLM, which drafts three ideas with different strategy directives. Each draft is validated: closed lists for hook, format and platform, and any number quoted in the rationale must match a real z-score from the data or the rationale is replaced.
- The trained classifier scores each draft and only the best is saved. The percentage is the model's probability that the idea beats the creator's 75th percentile, so the base rate is about 25 percent. The badge labels (Strong Fit, Worth Trying, Experimental) are display thresholds at 70 and 40 percent.
- "Best time" is text from the LLM. It is not used in the score. The score uses the creator's own best posting time from their winning posts.
- Click **Mark Actioned** or **Dismiss**. **Clear** only removes the card from the screen and does not touch the saved record. State plainly that this feedback is stored but does not change future recommendations yet.
- Under **Try Your Own Idea**, enter a topic the creator already posts about and a caption, and score it. Then enter an unfamiliar topic to show the amber note that the model has not seen it and ignored it.

### 5. History (30 seconds)

Open **History** to show the saved recommendations, newest first, with score and status. Only the winning candidate of each request is stored.

### 6. Under the hood (optional, 1 to 2 minutes)

- Swagger UI at `/docs` to show the endpoints. Try `/predict` or `/content` live.
- MLflow at `http://localhost:5001` shows the training runs. The classifier is the served model. The regressor is tracked but not used.
- State the evaluation honestly. The model recovers a signal planted in the synthetic data, and the reported metrics are on a per-user temporal split of that data. See [ml-pipeline.md](ml-pipeline.md) for the numbers and how to interpret them.

## Things that go wrong in a demo

| What you see | Why | Fix |
| --- | --- | --- |
| "Backend data isn't built yet" | `backend/data/` is empty | Run the pipeline from README step 5 |
| 404 or "no content" for a creator that exists | Typed ID, a half-pasted ID, or the creator was ingested after the last `build_features.py` | Paste the full ID, rebuild features |
| Errors that flicker while typing an ID | The selector reloads on every keystroke | Paste instead of typing |
| "Couldn't reach the server." | API down, or the page was opened on a different origin | Check `/health`, use `localhost:3000` |
| Recommendation fails with a 502 | Gemini key, model name, quota, timeout or safety block | Set `LLM_PROVIDER=mock` and recreate the API container |
| Same idea every time | Mock LLM | Expected |
| Leaderboard empty or short | The creator has few posts per platform and format group | Choose another creator |
| Old data after a rebuild | The browser caches GETs for 30 seconds | Wait or reload the page |
| Insights niche sections say "not enough data" | Small or partial dataset | Generate the full dataset, or explain the thresholds |
| 503 during `/recommend` after a pause | Model files were deleted or never trained | Run `train_model.py` |

## What not to claim

- That the model predicts real-world performance. It was trained on synthetic data with a planted signal.
- That insights are causal. They are descriptive averages with small samples.
- That feedback improves recommendations. It is stored only.
- That it connects to Instagram, YouTube or any other platform. All data arrives through `/ingest` from the generator.
- That it is secure for a shared deployment. There is no authentication. See [limitations.md](limitations.md).
