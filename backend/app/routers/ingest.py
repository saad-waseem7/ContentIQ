from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


@router.post("/ingest", response_model=schemas.IngestResponse, status_code=201)
def ingest(payload: schemas.IngestRequest, db: Session = Depends(get_db)):
    response = schemas.IngestResponse()
    try:
        if payload.user is not None:
            user = crud.get_or_create_user(db, payload.user)
            response.user_id = user.id

        if payload.channel is not None:
            channel = crud.get_or_create_channel(db, payload.channel)
            response.channel_id = channel.id

        if payload.content is not None:
            content, metrics_created = crud.create_content_with_metrics(db, payload.content)
            response.content_id = content.id
            response.metrics_created = metrics_created

        db.commit()
    except crud.DuplicateContentError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))

    return response