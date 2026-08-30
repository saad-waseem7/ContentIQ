"""
Orchestrates: grounding retrieval -> LLM candidate generation (N ideas) ->
feature-ization -> classifier scoring of EACH candidate -> best-candidate
selection -> persistence. Reuses leaderboard_service (grounding), llm.coach
(generation), ml.idea_scoring (scoring, called once per candidate) —
unchanged. Only the winning candidate is persisted; losing candidates are
scored, compared, then discarded (see module docstring / Checkpoint notes
on why this is a flagged-open product decision, not silently made).
"""
import uuid
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.leaderboard_service import get_user_feature_rows
from features.config import RECENT_POSTS_WINDOW
from features.embeddings import embed_texts
from llm.base import LLMClient
from llm.coach import generate_ideas
from ml.idea_scoring import score_idea

GROUNDING_TOP_K = 5
N_CANDIDATES = 3  # bounded by Gemini free-tier rate limits — see Checkpoint notes


class NoWinningContentError(Exception):
    """User has no label_overperformer=True posts to ground a recommendation in."""


class UnknownRecommendationError(Exception):
    pass


def _get_content_embeddings(db: Session, content_ids: list) -> dict:
    if not content_ids:
        return {}
    rows = db.execute(
        select(models.Content.id, models.Content.caption_embedding)
        .where(models.Content.id.in_(content_ids))
        .where(models.Content.caption_embedding.is_not(None))
    ).all()
    return {cid: np.array(vec, dtype=float) for cid, vec in rows}


def _build_base_user_context(db, user_df, winners_df) -> dict:
    """Fields that do NOT depend on which specific idea is being scored —
    computed once per request, not once per candidate."""
    content_ids = [uuid.UUID(cid) for cid in winners_df["content_id"]]
    embeddings_map = _get_content_embeddings(db, content_ids)
    centroid = np.mean(list(embeddings_map.values()), axis=0) if embeddings_map else None

    by_time = user_df.sort_values("posted_at")
    most_recent = by_time.iloc[-1]
    planned_posted_at = datetime.now(timezone.utc)
    days_since_last_post = (planned_posted_at - most_recent["posted_at"]).total_seconds() / 86400

    return {
        "niche": user_df["niche"].iloc[0],
        "follower_count": most_recent["follower_count"],
        "days_since_last_post": days_since_last_post,
        "is_first_post_for_user": False,
        "planned_posted_at": planned_posted_at,
        "_winner_centroid": centroid,
        "_recent_window_df": by_time.tail(RECENT_POSTS_WINDOW),
    }


def _complete_context_for_idea(base_context: dict, idea: dict, caption_embedding: np.ndarray) -> dict:
    """Fields that DO depend on the specific candidate idea — content_type_share_recent
    and similarity_to_prior_winners both vary per candidate (different content_type,
    different caption embedding). Formulas identical to the prior single-idea
    implementation — only WHEN they're computed changed, not the math."""
    recent_window = base_context["_recent_window_df"]
    content_type_share_recent = float((recent_window["content_type"] == idea["content_type"]).mean())

    centroid = base_context["_winner_centroid"]
    if centroid is not None:
        sim = float(np.dot(caption_embedding, centroid) / (np.linalg.norm(caption_embedding) * np.linalg.norm(centroid)))
    else:
        sim = None

    ctx = {k: v for k, v in base_context.items() if not k.startswith("_")}
    ctx["content_type_share_recent"] = content_type_share_recent
    ctx["similarity_to_prior_winners"] = sim
    return ctx


def _select_best_candidate(scored_candidates: list[tuple[dict, float]]) -> tuple[dict, float]:
    """Pure, directly unit-testable — no DB/LLM/model dependency."""
    return max(scored_candidates, key=lambda pair: pair[1])


def _format_idea_text(idea: dict) -> str:
    return f"[{idea['content_type']} / {idea['hook_type']} hook / {idea['primary_topic_tag']}] {idea['sample_caption']}"


def generate_recommendation(db: Session, user_id: str, llm_client: LLMClient) -> models.Recommendation:
    user_df = get_user_feature_rows(user_id)

    winners_df = user_df[user_df["has_sufficient_group_history"] & (user_df["label_overperformer"] == True)]  # noqa: E712
    if winners_df.empty:
        raise NoWinningContentError(f"User {user_id} has no top-performing content yet to ground a recommendation.")

    top_k = winners_df.sort_values("performance_z", ascending=False).head(GROUNDING_TOP_K)
    niche = user_df["niche"].iloc[0]

    ideas = generate_ideas(llm_client, niche=niche, grounding_posts=top_k.to_dict("records"), n=N_CANDIDATES)

    base_context = _build_base_user_context(db, user_df, winners_df)
    caption_embeddings = embed_texts([idea["sample_caption"] for idea in ideas])

    scored_candidates = []
    for idea, embedding in zip(ideas, caption_embeddings):
        caption_embedding = np.array(embedding)
        ctx = _complete_context_for_idea(base_context, idea, caption_embedding)
        score = score_idea(idea, ctx)
        scored_candidates.append((idea, score))

    best_idea, best_score = _select_best_candidate(scored_candidates)

    rec = models.Recommendation(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        idea_text=_format_idea_text(best_idea),
        format=best_idea["content_type"],
        best_time=best_idea["best_posting_window"],
        rationale=best_idea["rationale"],
        predicted_score=best_score,
        status="proposed",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def update_recommendation_status(db: Session, recommendation_id: str, status: str) -> models.Recommendation:
    rec = db.get(models.Recommendation, uuid.UUID(recommendation_id))
    if rec is None:
        raise UnknownRecommendationError(f"No recommendation found with id {recommendation_id}")
    rec.status = status
    db.commit()
    db.refresh(rec)
    return rec


def score_custom_idea(db: Session, user_id: str, idea: dict) -> float:
    """Scores a user-supplied idea directly, skipping LLM generation. Reuses
    the exact same context-building and scoring path generate_recommendation
    uses for each candidate — only the source of `idea` differs. Not
    persisted to `recommendations`: this is a one-off, on-demand check,
    per Feature doc — 'separate from the daily feed.'"""
    user_df = get_user_feature_rows(user_id)
    winners_df = user_df[user_df["has_sufficient_group_history"] & (user_df["label_overperformer"] == True)]  # noqa: E712
    if winners_df.empty:
        raise NoWinningContentError(f"User {user_id} has no top-performing content yet to score against.")

    base_context = _build_base_user_context(db, user_df, winners_df)
    caption_embedding = np.array(embed_texts([idea["sample_caption"]])[0])
    ctx = _complete_context_for_idea(base_context, idea, caption_embedding)
    return score_idea(idea, ctx)