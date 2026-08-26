from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import recommendation_service
from app.database import get_db
from app.leaderboard_service import FeatureDataNotBuiltError, UnknownUserError
from app.schemas import FeedbackRequest, RecommendationResponse
from llm.coach import IdeaGenerationError
from llm.factory import get_llm_client
from ml.idea_scoring import ModelArtifactsNotFoundError

router = APIRouter()

_llm_client = get_llm_client()


def _to_response(rec) -> RecommendationResponse:
    return RecommendationResponse(
        id=str(rec.id), idea_text=rec.idea_text, format=rec.format, best_time=rec.best_time,
        rationale=rec.rationale, predicted_score=rec.predicted_score, status=rec.status, created_at=rec.created_at,
    )


@router.post("/recommend", response_model=RecommendationResponse, status_code=201)
def create_recommendation(user_id: str, db: Session = Depends(get_db)):
    try:
        rec = recommendation_service.generate_recommendation(db, user_id, _llm_client)
    except FeatureDataNotBuiltError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ModelArtifactsNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except (UnknownUserError, recommendation_service.NoWinningContentError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IdeaGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _to_response(rec)


@router.post("/recommendations/{recommendation_id}/feedback", response_model=RecommendationResponse)
def submit_feedback(recommendation_id: str, payload: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        rec = recommendation_service.update_recommendation_status(db, recommendation_id, payload.status)
    except recommendation_service.UnknownRecommendationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _to_response(rec)