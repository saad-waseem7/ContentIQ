"""
Orchestrates: grounding retrieval -> LLM idea generation -> feature-ization
-> classifier scoring -> persistence. Reuses leaderboard_service (grounding),
llm.coach (generation), ml.idea_scoring (scoring). Only new responsibility
here: assembling user_context and the DB read/write for `recommendations`.
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
from llm.coach import generate_idea
from ml.idea_scoring import score_idea

GROUNDING_TOP_K = 5


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


def _build_user_context(db, user_df, winners_df, idea_content_type: str) -> dict:
    content_ids = [uuid.UUID(cid) for cid in winners_df["content_id"]]
    embeddings_map = _get_content_embeddings(db, content_ids)
    centroid = np.mean(list(embeddings_map.values()), axis=0) if embeddings_map else None

    by_time = user_df.sort_values("posted_at")
    most_recent = by_time.iloc[-1]
    recent_window = by_time.tail(RECENT_POSTS_WINDOW)
    content_type_share_recent = float((recent_window["content_type"] == idea_content_type).mean())

    planned_posted_at = datetime.now(timezone.utc)
    days_since_last_post = (planned_posted_at - most_recent["posted_at"]).total_seconds() / 86400

    return {
        "niche": user_df["niche"].iloc[0],
        "follower_count": most_recent["follower_count"],
        "days_since_last_post": days_since_last_post,
        "content_type_share_recent": content_type_share_recent,
        "is_first_post_for_user": False,
        "winner_centroid": centroid,
        "planned_posted_at": planned_posted_at,
    }


def _format_idea_text(idea: dict) -> str:
    return f"[{idea['content_type']} / {idea['hook_type']} hook / {idea['primary_topic_tag']}] {idea['sample_caption']}"


def generate_recommendation(db: Session, user_id: str, llm_client: LLMClient) -> models.Recommendation:
    user_df = get_user_feature_rows(user_id)  # raises UnknownUserError / FeatureDataNotBuiltError

    winners_df = user_df[user_df["has_sufficient_group_history"] & (user_df["label_overperformer"] == True)]  # noqa: E712
    if winners_df.empty:
        raise NoWinningContentError(f"User {user_id} has no top-performing content yet to ground a recommendation.")

    top_k = winners_df.sort_values("performance_z", ascending=False).head(GROUNDING_TOP_K)
    niche = user_df["niche"].iloc[0]
    idea = generate_idea(llm_client, niche=niche, grounding_posts=top_k.to_dict("records"))

    user_context = _build_user_context(db, user_df, winners_df, idea["content_type"])

    # Kept as a real np.ndarray from this point on — used for BOTH the
    # existing similarity-to-winners calc and the Week 5 PCA transform,
    # rather than converting twice.
    caption_embedding = np.array(embed_texts([idea["sample_caption"]])[0])
    centroid = user_context["winner_centroid"]
    if centroid is not None:
        sim = float(np.dot(caption_embedding, centroid) / (np.linalg.norm(caption_embedding) * np.linalg.norm(centroid)))
    else:
        sim = None
    user_context["similarity_to_prior_winners"] = sim

    predicted_score = score_idea(idea, user_context)

    rec = models.Recommendation(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        idea_text=_format_idea_text(idea),
        format=idea["content_type"],
        best_time=idea["best_posting_window"],
        rationale=idea["rationale"],
        predicted_score=predicted_score,
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