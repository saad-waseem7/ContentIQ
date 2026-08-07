# Columns available at prediction time — everything a coach would know about a
# post BEFORE it's published. Nothing here is derived from the post's outcome.
CATEGORICAL_FEATURES = [
    "content_type",
    "hook_type",
    "duration_bucket",
    "follower_tier",
    "niche",
    "platform",
    "primary_topic_tag",
]

NUMERIC_FEATURES = [
    "duration_sec",
    "caption_length_chars",
    "caption_length_words",
    "hashtag_count",
    "emoji_count",
    "has_cta",
    "posting_hour",
    "posting_day_of_week",
    "is_weekend",
    "sentiment_score",
    "follower_count",
    "days_since_last_post",
    "is_first_post_for_user",
    "content_type_share_recent",
    "similarity_to_prior_winners",
]

CLASSIFIER_TARGET = "label_overperformer"
REGRESSOR_TARGET = "performance_z"

# NEVER usable as model inputs: identifiers, raw text, or this row's OWN outcome
# metrics. Including any of these would let the model read the answer directly
# off the row instead of learning from pre-publish signal — the "own-row
# leakage" distinct from the future-row leakage builder.py already guards.
LEAKAGE_EXCLUDED_COLUMNS = [
    "content_id",
    "user_id",
    "title",
    "caption",
    "hashtags",
    "posted_at",
    "captured_at",
    "likes",
    "comments",
    "shares",
    "saves",
    "reach",
    "performance_raw",
    "performance_z",
    "label_overperformer",
    "has_sufficient_group_history",
]

# Fraction of each user's LATEST posts held out as test. Not specified by PRD.
# ~150-180 posts/user → ~30-36 test rows/user at 20%, enough for a per-user
# Spearman correlation to mean something without starving training data.
TEST_FRACTION_PER_USER = 0.2

RANDOM_SEED = 42

LGBM_CLASSIFIER_PARAMS = dict(
    objective="binary",
    n_estimators=200,
    num_leaves=31,
    learning_rate=0.05,
    random_state=RANDOM_SEED,
    verbose=-1,
    min_child_samples=10,  # default 20 blocks isolating the planted pattern (~20 examples/niche) — see Checkpoint diagnosis
)
LGBM_REGRESSOR_PARAMS = dict(
    objective="regression_l1",
    n_estimators=300,
    num_leaves=15,
    learning_rate=0.03,
    random_state=RANDOM_SEED,
    verbose=-1,
    min_child_samples=10,
)
MIN_TEST_ROWS_FOR_SPEARMAN = (
    3  # same reasoning as builder.py's MIN_GROUP_SIZE_FOR_ZSCORE
)

# Week 4 acceptance thresholds
ROC_AUC_THRESHOLD = 0.70
SPEARMAN_THRESHOLD = 0.40

MLFLOW_EXPERIMENT_NAME = "week4-baseline-model"

# Mirrors synthetic_data/config.py's PLANTED_SIGNAL exactly. Duplicated because
# api (backend/) and the generator (synthetic_data/) are separate Python
# environments with no shared import path — if synthetic_data/config.py's
# PLANTED_SIGNAL ever changes, this must be updated to match, or this
# verification will silently check against a stale pattern.
PLANTED_SIGNAL = {
    "fitness": {"hook_type": "story", "topic_tag": "transformation"},
    "food": {"hook_type": "listicle", "topic_tag": "quick_recipes"},
    "tech": {"hook_type": "bold_claim", "topic_tag": "product_review"},
}
