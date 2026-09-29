"""Generate grounded ideas, score them with the trained model, and persist the winner.

Scoring uses the user's historically best-performing posting time so an
idea's score does not depend on when the request was made. The LLM's
free-form best_posting_window remains display-only; days_since_last_post
still uses the current time because it describes actual posting recency.
"""
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
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
N_CANDIDATES = 3


class NoWinningContentError(Exception):
    """User has no label_overperformer=True posts to ground a recommendation in."""


class UnknownRecommendationError(Exception):
    pass


class UserNotFoundError(Exception):
    """No user exists with this id."""


def _get_content_embeddings(db: Session, content_ids: list) -> dict:
    if not content_ids:
        return {}
    rows = db.execute(
        select(models.Content.id, models.Content.caption_embedding)
        .where(models.Content.id.in_(content_ids))
        .where(models.Content.caption_embedding.is_not(None))
    ).all()
    return {cid: np.array(vec, dtype=float) for cid, vec in rows}


def _compute_best_posting_time(winners_df: pd.DataFrame, fallback_hour: int, fallback_weekday: int) -> tuple[int, int]:
    """Use the mode across winning posts, falling back when columns or values are missing.

    pandas sorts tied modes ascending, so the lowest value wins consistently.
    """
    required_cols = {"posting_hour", "posting_day_of_week"}
    if not required_cols.issubset(winners_df.columns):
        return fallback_hour, fallback_weekday

    valid = winners_df.dropna(subset=["posting_hour", "posting_day_of_week"])
    if valid.empty:
        return fallback_hour, fallback_weekday

    hour_mode = valid["posting_hour"].mode()
    weekday_mode = valid["posting_day_of_week"].mode()
    best_hour = int(hour_mode.iloc[0]) if not hour_mode.empty else fallback_hour
    best_weekday = int(weekday_mode.iloc[0]) if not weekday_mode.empty else fallback_weekday
    return best_hour, best_weekday

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

    best_posting_hour, best_posting_weekday = _compute_best_posting_time(
        winners_df,
        fallback_hour=planned_posted_at.hour,
        fallback_weekday=planned_posted_at.weekday(),
    )

    return {
        "niche": user_df["niche"].iloc[0],
        "follower_count": most_recent["follower_count"],
        "days_since_last_post": days_since_last_post,
        "is_first_post_for_user": False,
        "planned_posted_at": planned_posted_at,
        "best_posting_hour": best_posting_hour,
        "best_posting_weekday": best_posting_weekday,
        "_winner_centroid": centroid,
        "_recent_window_df": by_time.tail(RECENT_POSTS_WINDOW),
    }


def _complete_context_for_idea(base_context: dict, idea: dict, caption_embedding: np.ndarray) -> dict:
    """Add features that vary by candidate; shared user context is built once per request."""
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


def _format_idea_text(idea: dict) -> str:
    return f"[{idea['content_type']} / {idea['hook_type']} hook / {idea['primary_topic_tag']}] {idea['sample_caption']}"


def _select_best_candidate(scored_candidates: list[tuple[dict, float]]) -> tuple[dict, float]:
    """Select the highest-scoring candidate independently of persistence."""
    return max(scored_candidates, key=lambda pair: pair[1])


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


def score_custom_idea(db: Session, user_id: str, idea: dict) -> float:
    """Scores a user-supplied idea directly, skipping LLM generation. Reuses
    the exact same context-building and scoring path generate_recommendation
    uses for each candidate — only the source of `idea` differs. Not
    persisted to `recommendations`."""
    user_df = get_user_feature_rows(user_id)
    winners_df = user_df[user_df["has_sufficient_group_history"] & (user_df["label_overperformer"] == True)]  # noqa: E712
    if winners_df.empty:
        raise NoWinningContentError(f"User {user_id} has no top-performing content yet to score against.")

    base_context = _build_base_user_context(db, user_df, winners_df)
    caption_embedding = np.array(embed_texts([idea["sample_caption"]])[0])
    ctx = _complete_context_for_idea(base_context, idea, caption_embedding)
    return score_idea(idea, ctx)


def get_recommendation_history(db: Session, user_id: str) -> list[models.Recommendation]:
    user = db.get(models.User, uuid.UUID(user_id))
    if user is None:
        raise UserNotFoundError(f"No user found with id {user_id}")
    return (
        db.query(models.Recommendation)
        .filter(models.Recommendation.user_id == uuid.UUID(user_id))
        .order_by(models.Recommendation.created_at.desc())
        .all()
    )


def update_recommendation_status(db: Session, recommendation_id: str, status: str) -> models.Recommendation:
    rec = db.get(models.Recommendation, uuid.UUID(recommendation_id))
    if rec is None:
        raise UnknownRecommendationError(f"No recommendation found with id {recommendation_id}")
    rec.status = status
    db.commit()
    db.refresh(rec)
    return rec