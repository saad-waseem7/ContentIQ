"""
TEMPORARY diagnostic for the recommendation-score investigation.
Read-only. Does not modify any persisted data.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import numpy as np

from app import models
from app.database import SessionLocal
from app.leaderboard_service import get_user_feature_rows, UnknownUserError
from app.recommendation_service import _build_base_user_context, _complete_context_for_idea
from features.embeddings import embed_texts
from ml.idea_scoring import load_category_levels, load_classifier, score_idea, MODEL_PATH, CATEGORY_LEVELS_PATH

IDEA_PATTERN = re.compile(r"^\[(.+?)\s*/\s*(.+?)\s*hook\s*/\s*(.+?)\]", re.IGNORECASE)


def parse_idea_text(idea_text: str):
    m = IDEA_PATTERN.match(idea_text)
    if not m:
        return None, None, None
    return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()


def main():
    db = SessionLocal()

    print("=== Artifact freshness ===")
    print(f"classifier.joblib mtime: {MODEL_PATH.stat().st_mtime if MODEL_PATH.exists() else 'MISSING'}")
    print(f"category_levels.json mtime: {CATEGORY_LEVELS_PATH.stat().st_mtime if CATEGORY_LEVELS_PATH.exists() else 'MISSING'}")
    classifier = load_classifier()
    print(f"classifier.classes_: {getattr(classifier, 'classes_', 'N/A')}")

    print("\n=== Recent recommendations, raw stored values ===")
    recs = db.query(models.Recommendation).order_by(models.Recommendation.created_at.desc()).limit(20).all()
    for r in recs:
        content_type, hook_type, topic = parse_idea_text(r.idea_text)
        hour = r.created_at.hour
        weekday = r.created_at.weekday()
        print(f"\nid={r.id} score={r.predicted_score:.4f} ({r.predicted_score*100:.0f}%) "
              f"created_at={r.created_at} hour={hour} weekday={weekday}")
        print(f"  content_type={content_type} hook_type={hook_type} topic={topic}")
        print(f"  idea_text: {r.idea_text[:90]}")

    print("\n=== Sensitivity test: SAME idea, SAME user, posting_hour swept 0-23, everything else fixed ===")
    real_recs = [r for r in recs if parse_idea_text(r.idea_text)[0] is not None]
    if not real_recs:
        print("No real (non-test-fixture) recommendations found to test against.")
        db.close()
        return

    user_df, winners_df, base_context, chosen_user_id = None, None, None, None
    for candidate in real_recs:
        candidate_user_id = str(candidate.user_id)
        try:
            candidate_user_df = get_user_feature_rows(candidate_user_id)
        except UnknownUserError:
            continue  # this user_id has no rows in the current feature table — try the next real recommendation
        candidate_winners_df = candidate_user_df[
            candidate_user_df["has_sufficient_group_history"] & (candidate_user_df["label_overperformer"] == True)  # noqa: E712
        ]
        if candidate_winners_df.empty:
            continue  # user exists in features but has no winning content to ground a context on — try next
        user_df, winners_df, chosen_user_id = candidate_user_df, candidate_winners_df, candidate_user_id
        break

    if user_df is None:
        print("None of the recent real recommendations belong to a user currently present in features.parquet with winning content.")
        db.close()
        return

    print(f"Using user_id={chosen_user_id} for the sensitivity sweep.")
    base_context = _build_base_user_context(db, user_df, winners_df)
    test_idea = {
        "hook_type": "story", "content_type": "carousel", "platform": "instagram",
        "primary_topic_tag": "transformation", "duration_sec": None,
        "sample_caption": "Fixed test caption held constant across all hours.",
    }
    caption_embedding = np.array(embed_texts([test_idea["sample_caption"]])[0])

    anchor_time = base_context["planned_posted_at"]
    for hour in range(0, 24, 2):
        swept_context = dict(base_context)
        swept_context["planned_posted_at"] = anchor_time.replace(hour=hour, minute=0, second=0, microsecond=0)
        ctx = _complete_context_for_idea(swept_context, test_idea, caption_embedding)
        score = score_idea(test_idea, ctx)
        print(f"  hour={hour:02d} -> score={score:.4f} ({score*100:.0f}%)")

    db.close()


if __name__ == "__main__":
    main()