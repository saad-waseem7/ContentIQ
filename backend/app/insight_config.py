"""Thresholds for Insight aggregation and clustering, kept separate from service logic."""

"""
Dataset-scale review (post 125-user / 5-niche / ~21.5k-post expansion):
every threshold below was re-checked against actual current group sizes
(~24 other users per niche, several thousand posts per niche, ~172 posts
per user on average) and confirmed to still function correctly — none
block legitimate comparisons, none under-gate thin evidence. No value was
changed on the basis of dataset size alone: these are correctness
thresholds, not tuning knobs to inflate just because more data exists.
"""

# Require more evidence for a displayed pattern than for a training label.
PERSONAL_PATTERN_MIN_N = 5

TREND_MIN_N_PER_PERIOD = 5
TREND_RECENT_WINDOW_DAYS = 60
# Ignore smaller changes to avoid labeling ordinary variation as a trend.
TREND_DIRECTION_THRESHOLD = 0.3

MONTHLY_MIN_N = 3

NICHE_COMPARISON_MIN_OTHER_USERS = 10
NICHE_COMPARISON_MIN_TOTAL_POSTS = 50

# Population-level claims need more evidence than personal ones.
NICHE_PATTERN_MIN_N = 15
NICHE_PATTERN_TOP_K = 5

CLUSTER_MIN_NICHE_POSTS = 100
CLUSTER_K_RANGE = range(3, 7)
CLUSTER_MIN_SAMPLES_PER_CLUSTER = 5
# High-dimensional embeddings often have modest silhouette scores even when clusters are useful.
CLUSTER_SILHOUETTE_MIN = 0.12
CLUSTER_RANDOM_STATE = 42

TIME_WINDOWS = [
    ("night", range(0, 5)),
    ("morning", range(5, 12)),
    ("afternoon", range(12, 17)),
    ("evening", range(17, 22)),
    ("late_night", range(22, 24)),
]