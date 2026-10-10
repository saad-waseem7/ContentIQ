# Leaderboard and Insights

How every number on the Leaderboard and Insights screens is computed, which thresholds gate it, and how to read it. Code: `backend/app/leaderboard_service.py`, `backend/app/insight_service.py`, `backend/app/insight_config.py`, `backend/app/insight_clustering.py`, `backend/features/builder.py`. Neither screen calls the LLM or the classifier.

Both read `backend/data/features.parquet`, so they show the data as of the last `build_features.py` run. Only the topic clustering step touches PostgreSQL, to load caption embeddings.

## Shared definitions

These come from the feature table. The derivation, including the leakage safeguards, is in [ml-pipeline.md](ml-pipeline.md).

| Term | Meaning |
| --- | --- |
| `performance_raw` | `(likes + comments + shares + saves) / reach`, taken from the latest metric snapshot of the post. Posts without a usable `reach` are not in the feature table. |
| Group | One creator, one platform, one content type. Baselines never mix groups. |
| `performance_z` | `(performance_raw - mean) / std` over the group's **earlier** posts only, with sample standard deviation (`ddof=1`). If the earlier posts all have identical values (std of 0) the z-score is 0. |
| `label_overperformer` | True when `performance_raw` is above the 75th percentile of the group's earlier posts. |
| `has_sufficient_group_history` | True when the group has at least 3 earlier posts. Rows without it have no z-score and no label. |
| `n_prior_in_group` | How many earlier posts the group had when this post was published. It is the sample size behind this post's baseline. |

### n_prior_in_group

A z-score from 3 or 4 earlier points is noisy and tends to be extreme. `n_prior_in_group` makes that visible. Two thresholds use it:

- **Leaderboard ranking** requires `n_prior_in_group >= 10` (`MIN_PRIOR_POSTS_FOR_RANKING`).
- **Recommendation grounding** sorts posts with at least 10 earlier posts ahead of shallower ones, and uses the shallower ones only to fill the five slots.

Labels, training and Insights are not affected by the 10-post threshold. They use the 3-post minimum. This is a deliberate asymmetry: model training needs volume and tolerates label noise, while a ranked list shown to a person should not be topped by a post judged against three data points. It also means the Insights counts can be larger than the number of ranked leaderboard rows for the same creator.

Because the baseline is the creator's own group, a high z-score means "unusually good for this creator on this format", not "high engagement". A post at `performance_z` 3 with a raw rate of 2% can sit above one with a rate of 9% from another group.

## Leaderboard

`GET /content?user_id=...`

1. Take the creator's rows from the feature table.
2. Keep rows with `has_sufficient_group_history` and `n_prior_in_group >= 10`. If the column `n_prior_in_group` is missing (a feature table built by an older version of the pipeline) only the first condition applies.
3. Sort by `performance_z`, highest first, and number them from 1.

Response fields that need care:

| Field | Meaning |
| --- | --- |
| `total_posts_in_history` | All of the creator's rows in the feature table, including unranked ones. Posts without a usable reach are not counted. |
| `ranked_posts` | Rows that passed the filter above. The leaderboard list has this length. |
| `performance_raw` | The absolute engagement rate. Comparable within a group, not across platforms or formats. |
| `performance_z` | Standard deviations from this creator's earlier average for this group. |
| `is_top_performer` | The over-performer label: beat the 75th percentile of earlier posts in the group. A post can have a positive z-score and still be `false`. |

The first post of every group and the first nine after it never appear. A creator whose posts are spread thinly across many platform and format combinations can have a short or empty leaderboard even with hundreds of posts. The frontend shows the ranked count against the total.

The whole list is returned in one response. There is no paging.

## Insights

`GET /insights?user_id=...` returns six sections. Each is computed independently and each reports when it has too little data instead of guessing.

Unless stated otherwise, "valid rows" means rows with `has_sufficient_group_history` and a non-null `performance_z`. The primary topic of a post is the first entry of `topic_tags`, or `none` when the list is empty.

### Personal patterns

Mean `performance_z` of the creator's valid rows grouped by one dimension, for three dimensions:

- `hook_type`
- `topic` (primary topic)
- `posting_time_window`, from `posting_hour` (UTC): night 0 to 4, morning 5 to 11, afternoon 12 to 16, evening 17 to 21, late night 22 to 23

A value appears only with at least **5** posts (`PERSONAL_PATTERN_MIN_N`). `is_standout` is true when the mean z is above **0.5**. Results are sorted best first. `total_posts_analyzed` is the number of valid rows.

`content_type` is deliberately not a dimension. Each format has its own baseline, so z-scores say nothing about which format has higher absolute engagement.

Read it as: "when this creator used this hook, the post did on average X standard deviations better than the creator's usual for that format and platform." It is a descriptive average of a handful of posts, not a causal effect, and it has no significance test. Dimensions overlap (a topic and a hook are often used together), so two standouts can be the same posts.

Posting hours are UTC. There is no per-creator timezone, so the time-of-day windows describe UTC, not the audience's local time.

### Trend

Compares the creator's valid rows in the most recent **60** days against everything earlier. "Recent" is measured back from the creator's latest valid post, not from today, so an inactive creator still gets a trend.

- Both periods need at least **5** valid posts, otherwise `sufficient_data` is false and `direction` is `insufficient_data`.
- `direction` is `improving` if recent mean minus historical mean is above **0.3**, `declining` if below **-0.3**, otherwise `stable`.

The 0.3 threshold is a judgment call to avoid labeling noise, not a statistical test. Because every z-score is relative to the creator's own past, a creator who improved steadily in absolute terms can show a stable or even declining trend: the baseline keeps moving up with them.

### Monthly performance

Mean `performance_z` per calendar month (`YYYY-MM`, from `posted_at`) for months with at least **3** valid posts, in date order. Feeds the trend chart.

### Niche comparison

Compares absolute engagement, because `performance_z` cannot be compared between creators: each creator's own z-scores average near zero by construction.

1. Collect other creators' valid posts in the same niche.
2. For each platform and content type, take the median `performance_raw` of those posts.
3. Match the creator's valid posts to the medians for the same platform and content type. Posts whose group has no niche posts are dropped.
4. `engagement_ratio` is the creator's median `performance_raw` divided by the median of the matched niche medians.

Gates, all required: at least **10** other creators in the niche, at least **50** valid niche posts from them, and at least **5** of the creator's posts matched. Otherwise `sufficient_data` is false and the counts explain why. `user_n` in a successful response is the number of matched posts, which can be lower than the creator's valid post count.

A ratio of 1.2 means the creator's typical matched post has 20 percent more engagement per unit of reach than the niche's typical post of the same kind. It uses the reach-based rate on the latest snapshot, so it inherits the limits of that metric (reach is a platform-specific number and the synthetic data does not model platform differences in how it is reported).

### Niche top patterns

Hook type and primary topic across **all** valid posts in the creator's niche, including the creator's own, with at least **15** posts per value. The top **5** by mean `performance_z` are returned, tagged with their `dimension`. This is a niche-level view of "what tends to beat creators' own baselines here". It includes the creator's own posts, so a creator with many posts in the niche influences it.

### Topic clusters

Groups the niche's captions by meaning.

1. Load every caption embedding for the niche from PostgreSQL (all posts with an embedding, not only valid rows). Fewer than **100** embedded posts: `available` is false.
2. Run KMeans for k = 3 to 6 (`random_state=42`, `n_init=10`) on the 384-dimensional vectors and keep the k with the best silhouette score.
3. If the best silhouette score is below **0.12**, `available` is false and the score is reported. The threshold is intentionally low because silhouette scores on raw sentence embeddings are low even for real structure. It is a judgment call, not derived.
4. Join the labels to the niche's valid rows. Clusters with fewer than **5** valid posts are dropped. For each remaining cluster the response gives its size, mean `performance_z`, the majority content type, hook type and primary topic, and `is_high_performing` (mean z above 0.5). Clusters are sorted by mean z.
5. `user_cluster_summary` counts the selected creator's posts per cluster. It is built from every embedded post in the niche, so it includes posts that are not valid rows and clusters that were dropped from `clusters` for being small.

Clusters are not named by a model. The "dominant" labels are the most common values among members, so a cluster's description can be a weak summary if members are mixed. Cluster IDs are only meaningful within one response and one niche.

The result is cached per niche. The cache key is the niche's embedded-post count plus a fingerprint of its valid feature rows, so it recomputes after new embeddings or a rebuilt feature table. The cache is per API process. On a cold cache the request also loads the niche's embeddings and fits four KMeans models, so the first Insights request for a niche is slower than later ones. The size of that delay was not measured.

## Threshold summary

| Threshold | Value | Where |
| --- | --- | --- |
| Minimum earlier posts for a z-score and label | 3 | `features/config.py` |
| Minimum earlier posts to be ranked on the Leaderboard | 10 | `features/config.py` |
| Personal pattern minimum posts per value | 5 | `insight_config.py` |
| Standout and high-performing cut-off (mean z) | above 0.5 | `insight_service.py`, `insight_clustering.py` |
| Trend window and minimum posts per period | 60 days, 5 | `insight_config.py` |
| Trend direction delta | 0.3 | `insight_config.py` |
| Monthly minimum posts | 3 | `insight_config.py` |
| Niche comparison minimums | 10 other creators, 50 posts, 5 matched posts | `insight_config.py` |
| Niche pattern minimum posts and top K | 15, 5 | `insight_config.py` |
| Clustering minimum posts, k range, minimum cluster size, silhouette floor | 100, 3 to 6, 5, 0.12 | `insight_config.py` |

Changing a value in `features/config.py` that affects labels or `n_prior_in_group` requires rebuilding features and retraining. Changing `insight_config.py` takes effect after the API reloads (the dev server reloads on file save) and, for the cluster thresholds, only after the process restarts, because the cache key does not include the thresholds.
