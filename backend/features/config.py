# Bucket edges for duration_sec — content under 15s, 15-60s, 60-300s, 300s+.
# Not specified by PRD (It says "duration_sec (+ bucketed)" without edges).
# Chosen to roughly separate short-form/mid/long content across platforms in this dataset.
DURATION_BUCKETS = [0, 15, 60, 300, float("inf")]
DURATION_BUCKET_LABELS = ["under_15s", "15_to_60s", "60_to_300s", "over_300s"]

# Follower tier buckets — not specified by PRD ("follower tier (bucketed)").
# Matches the BASE_REACH/follower_count ranges already used by the Week 2 generator
# (500-200000), so buckets are meaningful against the actual synthetic distribution.
FOLLOWER_BUCKETS = [0, 5000, 50000, float("inf")]
FOLLOWER_BUCKET_LABELS = ["under_5k", "5k_to_50k", "over_50k"]

# Trailing window for "content-type share of recent posts" PRD - how many of the
# user's most recent prior posts to look at. Not specified; 10 is a reasonable
# recency window given users average ~180 posts.
RECENT_POSTS_WINDOW = 10

MIN_GROUP_SIZE_FOR_ZSCORE = (
    3  # same floor as user_baselines, avoids a meaningless z-score off 1-2 points
)

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
