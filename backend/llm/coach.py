"""
Prompt construction + idea generation for §10's LLM coaching layer.
Depends only on llm.base.LLMClient's generate() contract — no vendor coupling.
Validates output against the SAME closed lists already enforced elsewhere
(app.models.PLATFORMS/CONTENT_TYPES/HOOK_TYPES), not a re-declared copy.
"""
import json

from pydantic import BaseModel, ValidationError, field_validator

from app.models import CONTENT_TYPES, HOOK_TYPES, PLATFORMS
from llm.base import LLMClient, LLMGenerationError

MAX_ATTEMPTS = 2


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
        # Lightweight enforcement of §10's "must cite a real number" guardrail.
        # Confirms a digit is present — does not fact-check the number against
        # the grounding data (that would need parsing free text against
        # source stats, out of scope for this MVP).
        if not v or not v.strip() or not any(ch.isdigit() for ch in v):
            raise ValueError("rationale must cite a real number from the grounding data")
        return v


def _build_prompt(niche: str, grounding_posts: list[dict], retry_note: str = "") -> str:
    posts_summary = "\n".join(
        f"- {p['content_type']} with {p['hook_type']} hook on {p['topic_tags']}, "
        f"performance_z={p['performance_z']:.2f} standard deviations above this creator's own baseline"
        for p in grounding_posts
    )
    return f"""You are a content strategy coach for a creator in the "{niche}" niche.

This creator's real top-performing posts, ranked by how far above their OWN personal baseline they scored:
{posts_summary}

Generate exactly ONE new content idea grounded in these patterns. Respond with ONLY a JSON object with these exact keys:
hook_type (one of: question, bold_claim, listicle, story, none)
content_type (one of: short_video, long_video, image, carousel, text)
platform (one of: youtube, youtube_shorts, instagram, tiktok, x, linkedin)
primary_topic_tag (a short topic string)
duration_sec (integer seconds if video, otherwise null)
best_posting_window (short human-readable time window)
sample_caption (1-2 sentence sample caption/title)
rationale (ONE sentence, must cite a real number from the posts listed above — never invent a statistic)

Stay strictly within this creator's niche and voice.{retry_note}"""


def generate_idea(llm_client: LLMClient, niche: str, grounding_posts: list[dict]) -> dict:
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        retry_note = "\n\nYour previous response was invalid. Strictly follow the schema above." if attempt else ""
        prompt = _build_prompt(niche, grounding_posts, retry_note)
        try:
            raw = llm_client.generate(prompt)
        except LLMGenerationError as e:
            last_error = e
            continue
        try:
            idea = IdeaOutput(**json.loads(raw))
            return idea.model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            continue
    raise IdeaGenerationError(f"LLM failed to produce a valid idea after {MAX_ATTEMPTS} attempts: {last_error}")

def generate_ideas(llm_client: LLMClient, niche: str, grounding_posts: list[dict], n: int) -> list[dict]:
    """Generates up to n candidate ideas by calling generate_idea() independently
    n times — reuses its existing validation/retry logic unchanged. Tolerates
    partial failure: if some calls fail (malformed output, safety filter block,
    etc.) but at least one succeeds, returns whatever succeeded. Only raises if
    ALL n attempts fail."""
    ideas = []
    errors = []
    for _ in range(n):
        try:
            ideas.append(generate_idea(llm_client, niche=niche, grounding_posts=grounding_posts))
        except IdeaGenerationError as e:
            errors.append(str(e))
    if not ideas:
        raise IdeaGenerationError(f"Failed to generate any valid candidates after {n} attempts: {errors}")
    return ideas