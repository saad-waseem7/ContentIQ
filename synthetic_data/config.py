NICHES = ["fitness", "food", "tech", "beauty", "personal_finance"]

USERS_PER_NICHE = 25

MIN_POSTS_PER_USER = 150
MAX_POSTS_PER_USER = 200

METRIC_SNAPSHOT_DAYS_AFTER_POST = [1, 3, 7]

# Platforms available per niche, weighted — arbitrary but plausible per-niche skew,
# not stated in PRD, kept simple rather than exhaustively researched
NICHE_PLATFORMS = {
    "fitness": {"instagram": 0.4, "youtube_shorts": 0.3, "tiktok": 0.3},
    "food": {"instagram": 0.5, "youtube": 0.2, "tiktok": 0.3},
    "tech": {"youtube": 0.4, "x": 0.3, "linkedin": 0.3},
    "beauty": {"instagram": 0.5, "tiktok": 0.4, "youtube_shorts": 0.1},
    "personal_finance": {"youtube": 0.3, "x": 0.3, "linkedin": 0.4},
}

# Which content_types a platform realistically posts, weighted
PLATFORM_CONTENT_TYPES = {
    "instagram": {"image": 0.35, "carousel": 0.35, "short_video": 0.3},
    "youtube": {"long_video": 0.7, "short_video": 0.3},
    "youtube_shorts": {"short_video": 1.0},
    "tiktok": {"short_video": 1.0},
    "x": {"text": 0.5, "image": 0.3, "short_video": 0.2},
    "linkedin": {"text": 0.5, "image": 0.3, "carousel": 0.2},
}

HOOK_TYPES = ["question", "bold_claim", "listicle", "story", "none"]

TOPIC_TAGS_BY_NICHE = {
    "fitness": ["transformation", "workout_routine", "nutrition_tips", "recovery", "mindset"],
    "food": ["quick_recipes", "meal_prep", "restaurant_review", "baking", "healthy_eating"],
    "tech": ["product_review", "coding_tips", "ai_news", "gadget_unboxing", "career_advice"],
    "beauty": ["skincare_routine", "makeup_tutorial", "product_dupes", "hair_care", "self_care"],
    "personal_finance": ["budgeting", "investing_basics", "debt_payoff", "side_hustles", "saving_tips"],
}

# Content-type performance effects: multiplier applied to specific metrics
# (instagram, carousel) -> saves-heavy; (youtube_shorts/tiktok, short_video) -> view-heavy
CONTENT_TYPE_EFFECTS = {
    ("instagram", "carousel"): {"saves_multiplier": 2.5},
    ("youtube_shorts", "short_video"): {"views_multiplier": 3.0},
    ("tiktok", "short_video"): {"views_multiplier": 3.0},
}

# Was Tue/Thu, 7-9pm only (~2.4% of posts). Broadened to weekday evenings,
# a wider but still-plausible "prime posting time" window (~20% of posts),
# so the label's positive class has enough structured mass to be learnable.
BOOST_WEEKDAYS = [0, 1, 2, 3, 4]  # Monday-Friday
BOOST_HOURS = range(17, 21)  # 5pm-9pm
TIME_BOOST_MULTIPLIER = 1.8  # was 2.5 — lower per-post boost, but now hits ~8x more posts

# The hidden planted signal: (niche, hook_type, topic_tag) -> multiplier
# Used to verify that training recovers known niche-specific performance patterns.
PLANTED_SIGNAL = {
    "fitness": {"hook_type": "story", "topic_tag": "transformation", "multiplier": 5.0},
    "food": {"hook_type": "listicle", "topic_tag": "quick_recipes", "multiplier": 5.0},
    "tech": {"hook_type": "bold_claim", "topic_tag": "product_review", "multiplier": 5.0},
    "beauty": {"hook_type": "question", "topic_tag": "skincare_routine", "multiplier": 5.0},
    "personal_finance": {"hook_type": "story", "topic_tag": "debt_payoff", "multiplier": 5.0},
}

# Pareto shape parameter for power-law base performance draw.
# Lower alpha = heavier tail (more extreme viral outliers). 1.5 is a standard
# choice for social-media-style engagement power laws (not derived from real data,
# since this is synthetic — picked to produce a visibly heavy tail without
# absurd outliers that would break downstream aggregate stats)

PARETO_ALPHA = 3  

BASE_REACH_MIN = 500
BASE_REACH_MAX = 50000

API_BASE_URL = "http://localhost:8000"