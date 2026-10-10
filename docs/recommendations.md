# Recommendations

How `POST /recommend` turns a creator's history into one saved idea, and how `POST /predict` scores an idea the user typed. Code: `backend/app/recommendation_service.py`, `backend/llm/coach.py`, `backend/ml/idea_scoring.py`. The HTTP contract is in [api-reference.md](api-reference.md#post-recommend).

## Flow

```text
features.parquet rows for the user
   |  winners: label_overperformer = true AND has_sufficient_group_history
   v
top 5 grounding posts (prefer posts with >= 10 earlier posts in their group)
   |  plus a creator profile: modal platform, formats used, up to 25 topics
   v
3 parallel LLM calls, one strategy directive each (safe, alternative, experimental)
   |  each: parse JSON, validate enums, check rationale, normalize topic
   v
platform forced to the creator's modal platform
   |  caption embedded, feature row built, classifier scores it
   v
highest predicted_score wins -> saved to recommendations (status = proposed)
```

Nothing is written until a winner exists. A failure at any step before the insert leaves the database untouched.

## Step by step

1. **Load the creator's rows** from the feature table. Unknown creator: 404.
2. **Select winners.** Rows where `label_overperformer` is true and `has_sufficient_group_history` is true (at least 3 earlier posts in the group). None: 404 `has no top-performing content yet`.
3. **Check the user exists in PostgreSQL** before any LLM call. The feature table can list creators that were later deleted from the database, and the foreign key on `recommendations.user_id` would fail at the end. Failing early avoids paying for three LLM calls that cannot be saved.
4. **Pick grounding posts.** Up to 5 winners sorted by `performance_z`, with posts that have at least 10 earlier posts in their group (`MIN_PRIOR_POSTS_FOR_RANKING`) ranked ahead of shallower ones. Early posts have z-scores computed from very few points and are inflated, so they only fill the remaining slots. `n_prior_in_group` is explained in [insights-and-leaderboard.md](insights-and-leaderboard.md#n_prior_in_group).
5. **Build a creator profile.** The most common platform in the creator's rows, the formats used on that platform (most frequent first) and the creator's 25 most frequent primary topics. The prompt tells the model the platform and asks it to pick a topic from this list. This keeps ideas inside vocabulary the classifier has seen.
6. **Generate three candidates** with `ThreadPoolExecutor`, one thread each. Each gets a different strategy directive:
   - safest idea, mirroring the hook, format and topic that recur among the winners;
   - alternative framing, a different hook or format on a supported topic;
   - experimental, a less obvious combination or adjacent topic.
7. **Validate each candidate** (below). A candidate gets at most 2 attempts; the second prompt adds a note that the previous response was invalid. Both `LLMGenerationError` (provider failure, empty or blocked output) and parse or schema errors consume an attempt.
8. **Tolerate partial failure.** If at least one candidate is valid, the request continues with those. If none are, `IdeaGenerationError` becomes a 502 and nothing is saved.
9. **Override the platform** of every candidate with the creator's modal platform. The LLM is only told the platform in text, and scoring must use the real one.
10. **Score.** Embed all captions in one batch, build one feature row per candidate, apply the trained category levels, run the classifier.
11. **Persist the best.** `max` by predicted score, ties resolved by candidate order. Stored as `idea_text`, `format`, `best_time`, `rationale`, `predicted_score`, `status = proposed`.

The mock client is deterministic, so with `LLM_PROVIDER=mock` all three candidates are identical. That is expected and fine for demos of the flow, but it does not show variety.

## LLM output validation

The model must return one JSON object with these keys: `hook_type`, `content_type`, `platform`, `primary_topic_tag`, `duration_sec`, `best_posting_window`, `sample_caption`, `rationale`.

| Check | Failure effect |
| --- | --- |
| Not valid JSON, or not an object | Attempt consumed |
| `hook_type`, `content_type`, `platform` not in the closed lists | Attempt consumed |
| `primary_topic_tag`, `sample_caption`, `best_posting_window` empty | Attempt consumed |
| `rationale` contains no digit | Attempt consumed |
| Provider error, timeout or blocked response | Attempt consumed |

The Gemini client strips Markdown code fences from the reply before parsing, since the model often adds them.

After validation passes, two repairs run without consuming an attempt:

- **Topic mapping.** The topic is matched against the creator's own topics ignoring case, spaces and hyphens. If it does not match any, it is normalized (lowercase, spaces and hyphens to underscores). A normalized topic that the classifier never saw in training will be scored as missing.
- **Rationale grounding.** Every number in the rationale must be one of the listed `performance_z` values at the precision it is written (for example `11.45` must equal a listed z rounded to two places), or a whole number from 1 to the count of grounding posts. If any number fails, the rationale is replaced by a fixed sentence quoting the best grounding post's z-score. The idea itself is kept.

This guards against invented statistics. It does not check that the rationale is *true* in any other sense, only that the numbers come from the data given to the model. The idea text, hook and topic are not checked against the evidence at all beyond the closed lists.

## Scoring

`score_idea` builds one row with the same 22 model features used in training and returns the classifier's probability for the positive class.

- **Posting time is anchored to the creator's own history.** `posting_hour` and `posting_day_of_week` come from the mode across the winning posts (the lowest value wins ties). If the columns are missing or empty, the current UTC hour and weekday are used. This makes the score independent of when the request is made. The LLM's `best_posting_window` is display text only and plays no part in scoring.
- **Recency still uses the clock.** `days_since_last_post` is the wall-clock gap between now and the creator's latest post. For a synthetic dataset whose last posts are months in the past this value is large, and it drifts upward with every day the data ages. In the shipped data the effect on predicted scores was small (mean shift 0.053, maximum 0.148, measured during the handover review), but it is real and not frozen.
- **Context features** are computed once per request: creator niche, latest follower count, median hashtag count, content type share among the last 10 posts, and cosine similarity between the caption and the centroid of the winners' stored embeddings (`similarity_to_prior_winners`). If no winner has a stored embedding the similarity is missing.
- **Unknown categories.** Values outside the trained levels become missing, not an error. `follower_tier` is bucketed with the same edges as training.

The output is the probability that a post with these features would be an over-performer, meaning above the 75th percentile of the creator's earlier posts in its group. The base rate is about 0.25 by construction, so a score of 0.5 is already double the base rate. The frontend shows it as a percentage with a badge: 70% or more "Strong Fit", 40% or more "Worth Trying", below that "Experimental". Those cut-offs are arbitrary display choices, not calibrated thresholds.

What the score can and cannot mean:

- It ranks the three candidates against each other reasonably well to the extent the model does. Absolute values are not calibrated probabilities.
- The model learned a planted synthetic signal. Scores on real creators would need retraining and re-validation. See [ml-pipeline.md](ml-pipeline.md).
- Nothing checks that the format fits the platform (a `long_video` can be proposed for a creator whose channel is X). The creator's own formats are only a hint in the prompt.

## Custom idea scoring (`POST /predict`)

Same context building and scoring as above, with these differences:

- No LLM call, no database write, no PostgreSQL user check.
- The platform is taken from the request, not forced to the creator's own.
- The topic is mapped onto a trained level if it differs only in case, spaces or hyphens. Otherwise `topic_recognized` is `false` and the topic is scored as missing. The frontend shows an amber note in that case.
- `duration_sec` is optional and accepted without range checks.

Because the topic only has an effect when it matches something the model saw in training, a typed topic like "morning routine" may have no influence at all. The "Try Your Own Idea" panel says so when it happens.

## History and feedback

- `GET /recommendations` returns the creator's saved recommendations, newest first. Only the winner of each `/recommend` call is stored. The two losing candidates are discarded and cannot be recovered.
- `POST /recommendations/{id}/feedback` sets `actioned` or `dismissed`. Nothing consumes this signal. It does not influence later recommendations, retraining or grounding.

## Operational notes

- **Cost.** One request makes between 3 and 6 provider calls. There is no rate limit and no authentication.
- **Latency.** Candidates run in parallel, so latency is roughly one call, up to about two timeouts if the provider stalls (`GEMINI_TIMEOUT_SEC`, default 30). The first request after a restart also loads the embedding model.
- **Missing model files.** The 503 for a missing classifier is raised during scoring, after the LLM calls were already made.
- **Provider selection happens at import.** `get_llm_client()` runs once when the router module is imported. Change `LLM_PROVIDER` and recreate the API container.
- **Concurrency.** The mock and Gemini clients are shared across the three threads. The classifier is shared across requests. Read-only prediction on a shared booster is assumed safe and has not been load tested.
