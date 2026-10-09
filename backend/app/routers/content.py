"""Read-only leaderboard endpoint backed by the precomputed feature table."""
from fastapi import APIRouter, HTTPException, Query

from app import leaderboard_service
from app.schemas import LeaderboardResponse

router = APIRouter()


@router.get("/content", response_model=LeaderboardResponse)
def get_content_leaderboard(user_id: str = Query(..., description="UUID of the user")):
    try:
        result = leaderboard_service.build_leaderboard(user_id)
    except leaderboard_service.FeatureDataNotBuiltError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except leaderboard_service.UnknownUserError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result