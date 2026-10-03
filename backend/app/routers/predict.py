from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import recommendation_service
from app.database import get_db
from app.leaderboard_service import FeatureDataNotBuiltError, UnknownUserError
from app.schemas import PredictRequest, PredictResponse
from ml.idea_scoring import ModelArtifactsNotFoundError

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
def predict_idea(user_id: Annotated[str, Query(max_length=64)], payload: PredictRequest, db: Session = Depends(get_db)):
    try:
        result = recommendation_service.score_custom_idea(db, user_id, payload.model_dump())
    except FeatureDataNotBuiltError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ModelArtifactsNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except (UnknownUserError, recommendation_service.NoWinningContentError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PredictResponse(predicted_score=result.predicted_score, topic_recognized=result.topic_recognized)