# Duration buckets from short clips through long-form content.
DURATION_BUCKETS = [0, 15, 60, 300, float("inf")]
DURATION_BUCKET_LABELS = ["under_15s", "15_to_60s", "60_to_300s", "over_300s"]

# Buckets span the synthetic generator's follower-count range (500 to 200,000).
FOLLOWER_BUCKETS = [0, 5000, 50000, float("inf")]
FOLLOWER_BUCKET_LABELS = ["under_5k", "5k_to_50k", "over_50k"]

# Number of the user's previous posts included in content_type_share_recent.
RECENT_POSTS_WINDOW = 10

MIN_GROUP_SIZE_FOR_ZSCORE = (
    3  # same floor as user_baselines, avoids a meaningless z-score off 1-2 points
)

# A z-score built from only a few earlier posts is extreme and noisy, so posts with fewer than
# this many earlier posts in their group are not ranked on the leaderboard and are only used
# for recommendation grounding when nothing better exists. Labels and training are unaffected.
MIN_PRIOR_POSTS_FOR_RANKING = 10

CTA_PATTERNS = [
    r"\blink in bio\b",
    r"\bcomment below\b",
    r"\bdm me\b",
    r"\bswipe up\b",
    r"\bfollow for more\b",
    r"\bshare this\b",
    r"\btag a friend\b",
    r"\bsave this\b",
]
