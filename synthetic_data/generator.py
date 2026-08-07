import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg


def weighted_choice(options: dict) -> str:
    items = list(options.keys())
    weights = list(options.values())
    return random.choices(items, weights=weights, k=1)[0]


def random_posted_at() -> datetime:
    days_ago = random.randint(1, 365)
    hour = random.randint(0, 23)
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).replace(
        hour=hour, minute=random.choice([0, 15, 30, 45]), second=0, microsecond=0
    )


def compute_base_performance() -> float:
    """Pareto-distributed base performance ratio (engagement / reach), heavy-tailed."""
    raw = (np.random.pareto(cfg.PARETO_ALPHA) + 1) * 0.02
    return min(raw, 1.0)  # cap at 100% engagement rate, a ratio can't exceed reach


def apply_effects(base_perf: float, niche: str, platform: str, content_type: str, hook_type: str, topic_tag: str, posted_at: datetime) -> float:
    perf = base_perf

    if posted_at.weekday() in cfg.BOOST_WEEKDAYS and posted_at.hour in cfg.BOOST_HOURS:
        perf *= cfg.TIME_BOOST_MULTIPLIER

    signal = cfg.PLANTED_SIGNAL[niche]
    if hook_type == signal["hook_type"] and topic_tag == signal["topic_tag"]:
        perf *= signal["multiplier"]

    return perf


def saturating_growth(final_value: int, days_since_post: int, tau: float = 3.0) -> int:
    """Diminishing-returns growth curve: value climbs fast then plateaus."""
    fraction = 1 - np.exp(-days_since_post / tau)
    return max(0, round(final_value * fraction))


def generate_content_and_metrics(channel_id: str, niche: str, platform: str) -> dict:
    content_type = weighted_choice(cfg.PLATFORM_CONTENT_TYPES[platform])
    hook_type = random.choice(cfg.HOOK_TYPES)
    topic_tag = random.choice(cfg.TOPIC_TAGS_BY_NICHE[niche])
    posted_at = random_posted_at()

    base_perf = compute_base_performance()
    perf = apply_effects(base_perf, niche, platform, content_type, hook_type, topic_tag, posted_at)

    reach = random.randint(cfg.BASE_REACH_MIN, cfg.BASE_REACH_MAX)
    final_engaged = round(reach * perf)

    final_likes = round(final_engaged * 0.7)
    final_comments = round(final_engaged * 0.1)
    final_shares = round(final_engaged * 0.05)
    final_saves = round(final_engaged * 0.15)

    effect_key = (platform, content_type)
    if effect_key in cfg.CONTENT_TYPE_EFFECTS:
        effect = cfg.CONTENT_TYPE_EFFECTS[effect_key]
        if "saves_multiplier" in effect:
            final_saves = round(final_saves * effect["saves_multiplier"])
        if "views_multiplier" in effect:
            final_views_boost = effect["views_multiplier"]
        else:
            final_views_boost = 1.0
    else:
        final_views_boost = 1.0

    final_views = round(reach * random.uniform(1.2, 2.0) * final_views_boost)
    final_impressions = round(reach * random.uniform(1.1, 1.5))

    metrics = []
    for days in cfg.METRIC_SNAPSHOT_DAYS_AFTER_POST:
        metrics.append({
            "captured_at": (posted_at + timedelta(days=days)).isoformat(),
            "impressions": saturating_growth(final_impressions, days),
            "reach": saturating_growth(reach, days),
            "views": saturating_growth(final_views, days),
            "likes": saturating_growth(final_likes, days),
            "comments": saturating_growth(final_comments, days),
            "shares": saturating_growth(final_shares, days),
            "saves": saturating_growth(final_saves, days),
            "watch_time_sec": saturating_growth(random.randint(5, 120), days) if content_type in ("short_video", "long_video") else None,
            "avg_pct_watched": round(random.uniform(0.2, 0.9), 2) if content_type in ("short_video", "long_video") else None,
            "followers_gained": saturating_growth(round(final_engaged * 0.02), days),
        })

    return {
        "channel_id": channel_id,
        "content_type": content_type,
        "title": f"{niche} post about {topic_tag}",
        "caption": f"A {content_type} about {topic_tag} for my {niche} audience.",
        "hashtags": [f"#{niche}", f"#{topic_tag}"],
        "topic_tags": [topic_tag],
        "hook_type": hook_type,
        "duration_sec": random.randint(15, 600) if content_type in ("short_video", "long_video") else None,
        "posted_at": posted_at.isoformat(),
        "metrics": metrics,
    }


def ingest(payload: dict) -> dict:
    resp = requests.post(f"{cfg.API_BASE_URL}/ingest", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def run():
    random.seed(42)
    np.random.seed(42)

    summary = {"users": 0, "channels": 0, "content": 0, "metrics": 0}

    for niche in cfg.NICHES:
        for _ in range(cfg.USERS_PER_NICHE):
            user_resp = ingest({"user": {"niche": niche, "goal": "grow followers"}})
            user_id = user_resp["user_id"]
            summary["users"] += 1

            platform = weighted_choice(cfg.NICHE_PLATFORMS[niche])
            channel_resp = ingest({
                "channel": {
                    "user_id": user_id,
                    "platform": platform,
                    "handle": f"{niche}_{uuid.uuid4().hex[:8]}",
                    "follower_count": random.randint(500, 200000),
                }
            })
            channel_id = channel_resp["channel_id"]
            summary["channels"] += 1

            num_posts = random.randint(cfg.MIN_POSTS_PER_USER, cfg.MAX_POSTS_PER_USER)
            for _ in range(num_posts):
                content_payload = generate_content_and_metrics(channel_id, niche, platform)
                content_resp = ingest({"content": content_payload})
                summary["content"] += 1
                summary["metrics"] += content_resp["metrics_created"]

            print(f"  {niche} user {user_id[:8]}... ({platform}): {num_posts} posts ingested")

    print("\n=== Generation complete ===")
    print(summary)


if __name__ == "__main__":
    run()