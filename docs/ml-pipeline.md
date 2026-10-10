# ML pipeline

This document covers how data is generated, how performance is defined and labeled, how features are built, how the model is trained and evaluated, and what the metrics do and do not tell you. Serving-time use of the model is in [recommendations.md](recommendations.md).

## Synthetic data

`synthetic_data/generator.py` (settings in `synthetic_data/config.py`) posts creators to `/ingest`. There is no real data anywhere in the project.

| Property | Value |
| --- | --- |
| Niches | `fitness`, `food`, `tech`, `beauty`, `personal_finance` |
| Creators | 25 per niche, 125 total. Each has exactly one channel on one platform. |
| Posts per creator | 150 to 200 (about 21.5k in total), dated at random within the 365 days before the run |
| Metric snapshots | Three per post, at 1, 3 and 7 days after posting |
| Follower count | Uniform between 500 and 200,000 |
| Randomness | Seeded (`random` and NumPy, seed 42), but post dates are relative to the day you run it and IDs are random UUIDs, so two runs are never identical |

Each niche has a weighted platform mix, and each platform a weighted content-type mix (for example Instagram posts images, carousels and short videos, YouTube Shorts and TikTok only post short videos). Hook type and topic are chosen uniformly at random. Topics come from five per niche.

How a post's engagement is produced:

1. A base engagement rate is drawn from a heavy-tailed Pareto distribution (`(Pareto(3) + 1) * 0.02`, capped at 1.0).
2. Posts on Monday to Friday between 17:00 and 20:59 UTC are multiplied by 1.8.
3. Posts that match the niche's planted hook and topic are multiplied by 5.
4. Reach is a uniform draw between 500 and 50,000. Engagement is `reach x rate`, split 70% likes, 10% comments, 5% shares, 15% saves.
5. Instagram carousels get 2.5x saves, and views are multiplied by 3 on YouTube Shorts and TikTok short videos. These extra effects change the stored `saves` and `views` values only.
6. Every metric follows the same saturating growth curve across the three snapshots, so the engagement-to-reach ratio is almost the same at every snapshot.

The planted pairs are fitness (story, transformation), food (listicle, quick_recipes), tech (bold_claim, product_review), beauty (question, skincare_routine) and personal_finance (story, debt_payoff). Captions and titles are templates (`A <content_type> about <topic> for my <niche> audience.`), so the text carries no information beyond content type, topic and niche. Embedding-based features cannot reflect writing quality on this data.

`synthetic_data/validate.sql` holds SQL sanity checks for the generated data (counts per niche, posts per creator, three snapshots per post, skew, planted-signal lift). Its check 7 compares Tuesday and Thursday 19:00 to 20:59 against everything else, which is a narrower window than the generator's real boost (Monday to Friday, 17:00 to 20:59), so it understates the effect.

## Performance metric

```text
performance_raw = (likes + comments + shares + saves) / reach
```

It uses each post's latest metric snapshot. Missing engagement counts are treated as 0. Posts with zero or missing reach have no ratio and are dropped from the feature table. This is an engagement rate per person reached, not a view count.

## Relative performance and labels

Each post is compared with the same creator's earlier posts in the same group, where a group is `(user, platform, content_type)`. Groups are processed in posting order and a post is added to its group's history only after its own score is computed. This is an expanding window: the baseline for a post uses strictly earlier posts only.

For a post with at least 3 earlier posts in its group (`MIN_GROUP_SIZE_FOR_ZSCORE`):

```text
performance_z       = (performance_raw - mean(history)) / std(history)      # sample std (ddof=1); 0.0 if std is 0
label_overperformer = performance_raw > 75th percentile of history
```

Posts with fewer than 3 earlier posts get no `performance_z` and no label, and `has_sufficient_group_history` is false. `n_prior_in_group` records how many earlier posts were available.

Two things follow from this design:

- `performance_z` is unbounded and unclipped. A z-score computed from 3 to 9 earlier posts is noisy and can be very large (values above 10 appear in the data). Thresholds elsewhere account for it: the leaderboard ranks only posts with at least 10 earlier posts, and recommendation grounding prefers them (`MIN_PRIOR_POSTS_FOR_RANKING = 10`). Training and labeling still use every post with at least 3. The Insights screen also uses every post with at least 3 earlier posts, so its numbers include some noisy early z-scores that the leaderboard excludes.
- The label is "better than the top quartile of this creator's own past", so roughly 25% of labeled posts are positives by construction (26.4% in the shipped feature table).

`compute_baselines.py` also stores an all-history median, 25th and 75th percentile per group in `user_baselines`. Those are a serving-time snapshot. They are not used for labels, features, training or any endpoint.

## Feature table

`build_features.py` writes `backend/data/features.parquet` with 39 columns. Columns fall into four groups.

| Group | Columns |
| --- | --- |
| Identity and raw fields | `content_id`, `user_id`, `niche`, `platform`, `content_type`, `title`, `caption`, `hashtags`, `topic_tags`, `hook_type`, `duration_sec`, `posted_at`, `follower_count` |
| Latest metric snapshot | `captured_at`, `likes`, `comments`, `shares`, `saves`, `reach` |
| Outcome and history | `performance_raw`, `performance_z`, `label_overperformer`, `has_sufficient_group_history`, `n_prior_in_group` |
| Model inputs | `days_since_last_post`, `is_first_post_for_user`, `content_type_share_recent`, `similarity_to_prior_winners`, `caption_length_chars`, `caption_length_words`, `hashtag_count`, `emoji_count`, `has_cta`, `duration_bucket`, `posting_hour`, `posting_day_of_week`, `is_weekend`, `sentiment_score`, `follower_tier` |

### What the model is allowed to see

The classifier uses 22 columns, listed in `ml/config.py`. Everything else, including identifiers, text, raw metrics and every outcome column, is excluded, and a test asserts this.

| Feature | Meaning |
| --- | --- |
| `content_type`, `hook_type`, `platform`, `niche` | Categorical |
| `primary_topic_tag` | First entry of `topic_tags`, or `none` |
| `duration_bucket` | `under_15s`, `15_to_60s`, `60_to_300s`, `over_300s`, or `not_applicable` when there is no duration |
| `follower_tier` | `under_5k`, `5k_to_50k`, `over_50k`, or `unknown` |
| `duration_sec`, `follower_count` | Numeric, may be missing |
| `caption_length_chars`, `caption_length_words`, `hashtag_count`, `emoji_count` | Caption and tag counts |
| `has_cta` | Caption matches a call-to-action phrase such as "link in bio" or "save this" |
| `sentiment_score` | VADER compound score for the caption, 0 when there is no caption |
| `posting_hour`, `posting_day_of_week`, `is_weekend` | From `posted_at`. The hour is in UTC and Monday is 0. |
| `days_since_last_post` | Days since the creator's previous post on any platform or format. Missing for the first post. |
| `is_first_post_for_user` | True for the creator's first post |
| `content_type_share_recent` | Share of this post's content type among the creator's previous 10 posts. Missing for the first post. |
| `similarity_to_prior_winners` | Cosine similarity between this caption's embedding and the average embedding of the creator's earlier winning posts. Missing when there are no earlier winners or no embedding. |

LightGBM handles missing values natively and uses its own categorical splits, so no encoding or imputation step exists.

### Leakage safeguards

- Group baselines, labels, `days_since_last_post`, `content_type_share_recent` and `similarity_to_prior_winners` are all computed from strictly earlier posts only. The winner centroid inherits this because it is built from labels that are themselves history-only.
- The current post's own metrics produce its outcome and nothing else.
- `tests/test_feature_leakage.py` checks that changing a later post's metrics cannot change an earlier post's features or label, that a group's first posts get no label, that `days_since_last_post` uses only the previous post, and that `n_prior_in_group` counts only earlier posts within the same group. `tests/test_data_prep.py` checks that every train and test split keeps test rows later than train rows per creator and that excluded columns never reach the model matrix.

## Training and evaluation

`train_model.py` runs these steps.

1. Load `features.parquet` and drop rows without a label (no valid history).
2. **Split by time per creator.** Each creator's labeled posts are sorted by `posted_at`. The last 20% (at least one post) go to the test set and the rest to training. The split is per creator, not a single global cutoff date, so a training row from one creator can be later in calendar time than a test row from another. It measures forward-in-time prediction for creators the model has already seen, not generalization to new creators.
3. Train a LightGBM classifier on `label_overperformer` and a LightGBM regressor on `performance_z`, both on the training rows only.
4. **Write the serving files**: `category_levels.json`, then `classifier.joblib`. The classifier that serves traffic is the one trained on the 80% split. It is not refit on all rows.
5. Evaluate on the test rows, compare with a baseline, run SHAP, log everything to MLflow, and print an acceptance summary.

Hyperparameters (`ml/config.py`, fixed seed 42):

| | Classifier | Regressor |
| --- | --- | --- |
| Objective | `binary` | `regression_l1` |
| Trees | 200 | 300 |
| Leaves | 31 | 15 |
| Learning rate | 0.05 | 0.03 |
| `min_child_samples` | 10 | 10 |

**Metrics.**

- Classifier: ROC-AUC and PR-AUC on the held-out rows.
- Regressor: Spearman rank correlation between predicted and actual `performance_z`, computed per creator and averaged. Creators with fewer than 3 test rows, or a constant series, are skipped.
- Baseline: for each content type, the training-set mean of the target, applied to test rows of that content type.
- Acceptance thresholds in config: ROC-AUC at least 0.70 and Spearman at least 0.40. The script prints PASS or FAIL, but a FAIL changes nothing.

**SHAP.** `shap.TreeExplainer` runs on the test rows. The script prints the 10 most important features and checks, per niche, that the topic and hook SHAP values for the planted pair are higher on average than for other posts. A niche is skipped if the test set has no matching or no non-matching row.

**MLflow.** Experiment `week4-baseline-model`, run `week4-lightgbm-baseline`. It logs a SHA-256 of `features.parquet`, train and test row counts, all hyperparameters, five metrics (classifier ROC-AUC, PR-AUC and baseline ROC-AUC, regressor Spearman and baseline Spearman), both models, a JSON summary, and the SHAP importance table and plot. The names contain "week4" for historical reasons.

### Results on the shipped dataset

The feature table in the project hand-off has 21,587 rows. It has 153 creators: the 125 generated ones plus 28 single-post `fitness` creators that earlier backend test runs added to the development database (see [development.md](development.md#testing)). They have no labels and do not affect training. 20,725 rows carry a label, giving 16,630 training rows and 4,095 test rows.

These figures were reproduced during the handover by running the repository's own preparation, training and evaluation code on that file. The shipped classifier and a freshly retrained one produced identical scores, so training is deterministic for this data and configuration.

| Metric (test set) | Classifier | Content-type baseline |
| --- | --- | --- |
| ROC-AUC | 0.7498 | 0.5054 |
| PR-AUC | 0.6397 | 0.2436 |
| Regressor Spearman (per creator, averaged) | 0.3441 | 0.0672 |

The test-set positive rate is 24.2%, so a model with no skill would score a PR-AUC near 0.24.

### How to read these numbers

- ROC-AUC 0.75 means the classifier ranks a random over-performer above a random non-over-performer 75% of the time. The baseline sits at chance.
- The classifier meets its 0.70 target. The regressor does not meet its 0.40 target and is not used for serving. The project attributes the gap to the synthetic label being mostly noise by design. Five tuning attempts and a PCA experiment did not close it, and the PCA run lowered both headline metrics (recorded in the project's earlier notes, not rerun for this handover).
- The data is synthetic with a deliberately planted 5x signal, an hour-of-day effect and templated text. Strong recovery of that signal shows the pipeline works and has no leakage. It says little about accuracy on real creators.
- `predicted_score` is the classifier's raw probability. Nothing in the code calibrates it, so 0.8 should be read as "ranks high", not as an 80% chance.

## Embeddings

`generate_embeddings.py` encodes `title + caption` with `all-MiniLM-L6-v2` (384 dimensions, vectors normalized to unit length) and stores them in `content.caption_embedding`. The Docker image downloads the model at build time. The embeddings feed three things: `similarity_to_prior_winners`, topic clustering on the Insights page, and the same similarity feature at serving time.

`ml/embedding_reduction.py` and `scripts/train_model_pca_experiment.py` form an optional experiment that reduces embeddings with PCA fitted on training rows only. It writes to `backend/data/experiments/` and does not touch the serving model.

## Artifacts and consistency

| File | Written by | Purpose |
| --- | --- | --- |
| `backend/data/features.parquet` | `build_features.py` | Leaderboard, insights, recommendation context, training input |
| `backend/data/classifier.joblib` | `train_model.py` | Serving classifier |
| `backend/data/category_levels.json` | `train_model.py` | The category vocabulary the classifier was trained with |

At serving time the categorical columns are rebuilt with the saved levels, in the same order, so category codes line up with training. Values the model has never seen become missing. All three files are replaced atomically. The two model files must come from one training run.

`joblib` files are Python pickles. Load only files produced by your own pipeline.
