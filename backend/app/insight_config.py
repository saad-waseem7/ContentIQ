"""
Config for the Week 6 Insight Engine. Kept separate from insight_service.py's
logic — same convention as features/config.py vs builder.py, ml/config.py
vs ml/*.py. Every threshold here exists to enforce one explicit principle:
never present a statistically weak group as a strong insight.
"""

# Stricter than features.config.MIN_GROUP_SIZE_FOR_ZSCORE (3) — that
# threshold protects the MODEL's training labels from too-few-point groups;
# this protects a HUMAN-FACING claim, which warrants more evidence.
PERSONAL_PATTERN_MIN_N = 5

TREND_MIN_N_PER_PERIOD = 5
TREND_RECENT_WINDOW_DAYS = 60
# Minimum delta (performance_z units) before labeling a direction rather
# than "stable" — avoids calling ordinary noise a trend.
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
# Judgment call, not derived: silhouette scores on raw high-dimensional
# sentence embeddings are typically low even for genuinely separable
# clusters, so this is deliberately more permissive than the textbook
# "0.5 = good" guideline, which would reject almost everything at this
# dimensionality.
CLUSTER_SILHOUETTE_MIN = 0.12
CLUSTER_RANDOM_STATE = 42

TIME_WINDOWS = [
    ("night", range(0, 5)),
    ("morning", range(5, 12)),
    ("afternoon", range(12, 17)),
    ("evening", range(17, 22)),
    ("late_night", range(22, 24)),
]