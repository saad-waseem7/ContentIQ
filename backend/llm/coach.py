"""
Prompt construction + idea generation for LLM coaching layer.
Depends only on llm.base.LLMClient's generate() contract — no vendor coupling.
Validates output against the SAME closed lists already enforced elsewhere
(app.models.PLATFORMS/CONTENT_TYPES/HOOK_TYPES), not a re-declared copy.
"""

import json
import concurrent.futures
import re

from pydantic import BaseModel, ValidationError, field_validator

from app.models import CONTENT_TYPES, HOOK_TYPES, PLATFORMS
from features.topics import match_topic, normalize_topic
from llm.base import LLMClient, LLMGenerationError

MAX_ATTEMPTS = 2

# These directions encourage variety without overriding evidence from the creator's posts.
STRATEGY_DIRECTIVES = [
    "Strategic direction: propose the SAFEST, most evidence-backed idea — "
    "closely mirror the hook type, content type, and topic that appear most "
    "consistently among the top-performing posts above.",
    "Strategic direction: propose an ALTERNATIVE FRAMING. Keep the idea "
    "grounded in the same posts above, but present it differently than the "
    "single most obvious choice — e.g. a different hook type or content "
    "type than your first instinct, while staying on a topic these posts support.",
    "Strategic direction: propose a more EXPERIMENTAL idea that still draws "
    "directly on the creator's demonstrated strengths above, but combines "
    "them in a less obvious way — e.g. a different angle, structure, or an "
    "adjacent topic — while remaining clearly grounded in the evidence given.",
]


class IdeaGenerationError(Exception):
    """LLM output could not be parsed/validated after MAX_ATTEMPTS tries,
    or the underlying call failed on every attempt."""


class IdeaOutput(BaseModel):
    hook_type: str
    content_type: str
    platform: str
    primary_topic_tag: str
    duration_sec: int | None = None
    best_posting_window: str
    sample_caption: str
    rationale: str

    @field_validator("hook_type")
    @classmethod
    def check_hook_type(cls, v):
        if v not in HOOK_TYPES:
            raise ValueError(f"hook_type must be one of {HOOK_TYPES}")
        return v

    @field_validator("content_type")
    @classmethod
    def check_content_type(cls, v):
        if v not in CONTENT_TYPES:
            raise ValueError(f"content_type must be one of {CONTENT_TYPES}")
        return v

    @field_validator("platform")
    @classmethod
    def check_platform(cls, v):
        if v not in PLATFORMS:
            raise ValueError(f"platform must be one of {PLATFORMS}")
        return v

    @field_validator("primary_topic_tag", "sample_caption", "best_posting_window")
    @classmethod
    def check_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("field must not be empty")
        return v

    @field_validator("rationale")
    @classmethod
    def check_rationale_cites_a_number(cls, v):
        if not v or not v.strip() or not any(ch.isdigit() for ch in v):
            raise ValueError(
                "rationale must cite a real number from the grounding data"
            )
        return v


_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")


def _rationale_is_grounded(rationale: str, grounding_posts: list[dict]) -> bool:
    """Accept listed performance_z values at the cited precision and integers from 1 through the post count."""
    z_values = [float(p["performance_z"]) for p in grounding_posts]
    for token in _NUMBER_PATTERN.findall(rationale):
        decimals = len(token.split(".")[1]) if "." in token else 0
        value = float(token)
        matches_z = any(abs(round(z, decimals) - value) < 1e-9 for z in z_values)
        is_count = decimals == 0 and 1 <= value <= len(grounding_posts)
        if not (matches_z or is_count):
            return False
    return True


def _fallback_rationale(grounding_posts: list[dict]) -> str:
    best_z = max(float(p["performance_z"]) for p in grounding_posts)
    return (
        f"Your strongest post of this kind scored {best_z:.2f} standard deviations above "
        "your own baseline, and this idea builds on that pattern."
    )


def _build_prompt(
    niche: str,
    grounding_posts: list[dict],
    retry_note: str = "",
    directive: str = "",
    creator_profile: dict | None = None,
) -> str:
    profile = creator_profile or {}
    platform = profile.get("platform")
    formats = profile.get("content_types") or []
    topics = profile.get("topics") or []

    posts_summary = "\n".join(
        f"- {p['content_type']} with {p['hook_type']} hook on {p['topic_tags']}, "
        f"performance_z={p['performance_z']:.2f} standard deviations above this creator's own baseline"
        for p in grounding_posts
    )
    directive_block = f"\n\n{directive}" if directive else ""
    platform_line = f"\nThis creator publishes on {platform}." if platform else ""
    platform_key = (
        f"platform (must be exactly: {platform})"
        if platform
        else "platform (one of: youtube, youtube_shorts, instagram, tiktok, x, linkedin)"
    )
    format_hint = f" This creator already uses: {', '.join(formats)}." if formats else ""
    topic_key = (
        f"primary_topic_tag (use one of this creator's existing topics, written exactly as shown: {', '.join(topics)})"
        if topics
        else "primary_topic_tag (a short topic string)"
    )
    return f"""You are a content strategy coach for a creator in the "{niche}" niche.{platform_line}

This creator's real top-performing posts, ranked by how far above their OWN personal baseline they scored:
{posts_summary}

Generate exactly ONE new content idea grounded in these patterns.{directive_block} Respond with ONLY a JSON object with these exact keys:
hook_type (one of: question, bold_claim, listicle, story, none)
content_type (one of: short_video, long_video, image, carousel, text){format_hint}
{platform_key}
{topic_key}
duration_sec (integer seconds if video, otherwise null)
best_posting_window (short human-readable time window)
sample_caption (1-2 sentence sample caption/title)
rationale (ONE sentence, must cite a performance_z value exactly as listed above — never invent a statistic)

Stay strictly within this creator's niche and voice.{retry_note}"""


def generate_idea(
    llm_client: LLMClient,
    niche: str,
    grounding_posts: list[dict],
    directive: str = "",
    creator_profile: dict | None = None,
) -> dict:
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        retry_note = (
            "\n\nYour previous response was invalid. Strictly follow the schema above."
            if attempt
            else ""
        )
        prompt = _build_prompt(niche, grounding_posts, retry_note, directive, creator_profile)
        try:
            raw = llm_client.generate(prompt)
        except LLMGenerationError as e:
            last_error = e
            continue
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"expected a JSON object, got {type(parsed).__name__}")
            idea = IdeaOutput(**parsed).model_dump()
        except ValueError as e:  # JSONDecodeError and pydantic's ValidationError are both ValueErrors
            last_error = e
            continue
        return _finalize_idea(idea, grounding_posts, creator_profile)
    raise IdeaGenerationError(
        f"LLM failed to produce a valid idea after {MAX_ATTEMPTS} attempts: {last_error}"
    )


def _finalize_idea(idea: dict, grounding_posts: list[dict], creator_profile: dict | None) -> dict:
    """Normalize topic spelling and replace an ungrounded rationale with a fallback."""
    topics = (creator_profile or {}).get("topics") or []
    idea["primary_topic_tag"] = match_topic(idea["primary_topic_tag"], topics) or normalize_topic(
        idea["primary_topic_tag"]
    )
    if grounding_posts and not _rationale_is_grounded(idea["rationale"], grounding_posts):
        idea["rationale"] = _fallback_rationale(grounding_posts)
    return idea


def generate_ideas(
    llm_client: LLMClient,
    niche: str,
    grounding_posts: list[dict],
    n: int,
    creator_profile: dict | None = None,
) -> list[dict]:
    """Generate candidates concurrently and keep successful results when others fail.

    The shared client must support concurrent calls. IdeaGenerationError from one
    candidate is tolerated unless every candidate fails.
    """
    directives = [STRATEGY_DIRECTIVES[i % len(STRATEGY_DIRECTIVES)] for i in range(n)]
    ideas: list[dict | None] = [None] * n
    errors: list[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        future_to_index = {
            executor.submit(
                generate_idea, llm_client, niche, grounding_posts, directives[i], creator_profile
            ): i
            for i in range(n)
        }
        for future in concurrent.futures.as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                ideas[idx] = future.result()
            except IdeaGenerationError as e:
                errors.append(str(e))

    successful = [idea for idea in ideas if idea is not None]

    if not successful:
        raise IdeaGenerationError(
            f"Failed to generate any valid candidates after {n} attempts: {errors}"
        )
    return successful
