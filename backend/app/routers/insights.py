from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import insight_service
from app.database import get_db
from app.leaderboard_service import FeatureDataNotBuiltError, UnknownUserError
from app.schemas import InsightsResponse

router = APIRouter()


@router.get("/insights", response_model=InsightsResponse)
def get_insights(user_id: str, db: Session = Depends(get_db)):
    try:
        return insight_service.build_insights(db, user_id)
    except FeatureDataNotBuiltError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except UnknownUserError as e:
        raise HTTPException(status_code=404, detail=str(e))