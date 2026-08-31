"""
TEMPORARY diagnostic script for the Recommendation Quality Evaluation.
Not part of the shipped app — does not persist to `recommendations`.
Reuses real production functions (generate_ideas, context-building, score_idea)
rather than duplicating any scoring/generation logic. Safe to delete after use.
"""
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.database import SessionLocal
from app.insight_service import personal_pattern_insights, build_user_niche_frames
from app.leaderboard_service import load_feature_table
from app.recommendation_service import (
    GROUNDING_TOP_K, _build_base_user_context, _complete_context_for_idea,
)

from features.embeddings import embed_texts
from llm.coach import generate_ideas
from llm.factory import get_llm_client
from ml.idea_scoring import score_idea

USERS_PER_NICHE_TO_SAMPLE = 1


def pick_sample_users(df, niche: str, n: int):
    niche_df = df[df["niche"] == niche]
    winners = niche_df[niche_df["has_sufficient_group_history"] & (niche_df["label_overperformer"] == True)]  # noqa: E712
    counts = winners.groupby("user_id").size()
    eligible = counts[counts >= GROUNDING_TOP_K].index.tolist()
    return eligible[:n]


def evaluate_user(db, user_id: str, llm_client) -> dict:
    user_df, niche_df, niche = build_user_niche_frames(user_id)
    winners_df = user_df[user_df["has_sufficient_group_history"] & (user_df["label_overperformer"] == True)]  # noqa: E712
    top_k = winners_df.sort_values("performance_z", ascending=False).head(GROUNDING_TOP_K)

    standout_dims = personal_pattern_insights(user_df)["dimensions"]
    standout_values = set()
    for entries in standout_dims.values():
        for e in entries:
            if e["is_standout"]:
                standout_values.add(e["value"])

    ideas = generate_ideas(llm_client, niche=niche, grounding_posts=top_k.to_dict("records"), n=3)

    base_context = _build_base_user_context(db, user_df, winners_df)
    captions = [idea["sample_caption"] for idea in ideas]
    embeddings = embed_texts(captions)

    results = []
    for idea, emb in zip(ideas, embeddings):
        ctx = _complete_context_for_idea(base_context, idea, np.array(emb))
        score = score_idea(idea, ctx)
        matches_standout = any(idea.get(k) in standout_values for k in ("hook_type", "content_type", "primary_topic_tag"))
        results.append({
            "hook_type": idea["hook_type"], "content_type": idea["content_type"],
            "topic": idea["primary_topic_tag"], "caption": idea["sample_caption"][:80],
            "score": round(score, 4), "matches_a_standout_personal_pattern": matches_standout,
        })

    scores = [r["score"] for r in results]
    distinct_hook_types = len(set(r["hook_type"] for r in results))
    distinct_content_types = len(set(r["content_type"] for r in results))
    distinct_topics = len(set(r["topic"] for r in results))
    winner = max(results, key=lambda r: r["score"])

    return {
        "user_id": user_id, "niche": niche, "candidates": results,
        "score_spread": round(max(scores) - min(scores), 4),
        "distinct_hook_types": distinct_hook_types, "distinct_content_types": distinct_content_types,
        "distinct_topics": distinct_topics, "winner_matches_standout": winner["matches_a_standout_personal_pattern"],
        "standout_personal_patterns": sorted(standout_values),
    }


def main():
    df = load_feature_table()
    llm_client = get_llm_client()
    db = SessionLocal()

    all_results = []
    try:
        niches = sorted(df["niche"].dropna().unique().tolist())
        for niche in niches:
            user_ids = pick_sample_users(df, niche, USERS_PER_NICHE_TO_SAMPLE)
            for user_id in user_ids:
                print(f"\n=== Evaluating {niche} / {user_id[:8]}... ===")
                try:
                    result = evaluate_user(db, user_id, llm_client)
                    all_results.append(result)
                    print(f"Standout personal patterns: {result['standout_personal_patterns']}")
                    for c in result["candidates"]:
                        print(f"  [{c['score']:.3f}] {c['content_type']}/{c['hook_type']}/{c['topic']} "
                              f"(standout match: {c['matches_a_standout_personal_pattern']}) — {c['caption']}")
                    print(f"Score spread: {result['score_spread']} | Distinct hook_types: {result['distinct_hook_types']}"
                          f" | Distinct content_types: {result['distinct_content_types']} | Distinct topics: {result['distinct_topics']}"
                          f" | Winner matches a standout pattern: {result['winner_matches_standout']}")
                except Exception as e:
                    print(f"  SKIPPED due to error: {e}")
                time.sleep(2)  # spacing calls to reduce risk of hitting Gemini free-tier rate limits
    finally:
        db.close()

    print("\n\n=== AGGREGATE SUMMARY ===")
    if not all_results:
        print("No results collected.")
        return
    avg_spread = np.mean([r["score_spread"] for r in all_results])
    pct_all_same_hook = np.mean([r["distinct_hook_types"] == 1 for r in all_results]) * 100
    pct_all_same_content_type = np.mean([r["distinct_content_types"] == 1 for r in all_results]) * 100
    pct_all_same_topic = np.mean([r["distinct_topics"] == 1 for r in all_results]) * 100
    pct_winner_matches = np.mean([r["winner_matches_standout"] for r in all_results]) * 100
    print(f"Users evaluated: {len(all_results)}")
    print(f"Average score spread across 3 candidates: {avg_spread:.4f}")
    print(f"% of users where all 3 candidates shared the same hook_type: {pct_all_same_hook:.0f}%")
    print(f"% of users where all 3 candidates shared the same content_type: {pct_all_same_content_type:.0f}%")
    print(f"% of users where all 3 candidates shared the same topic: {pct_all_same_topic:.0f}%")
    print(f"% of users where the winning candidate matched a standout personal pattern: {pct_winner_matches:.0f}%")


if __name__ == "__main__":
    main()