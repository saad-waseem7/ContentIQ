import uuid
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from app import models, schemas
from sqlalchemy import update

def get_or_create_user(db: Session, user_in: schemas.UserIngest) -> models.User:
    if user_in.id is not None:
        existing = db.get(models.User, user_in.id)
        if existing is not None:
            return existing
    user = models.User(id=user_in.id or uuid.uuid4(), niche=user_in.niche, goal=user_in.goal)
    db.add(user)
    db.flush()
    return user


def get_or_create_channel(db: Session, channel_in: schemas.ChannelIngest) -> models.Channel:
    if channel_in.id is not None:
        existing = db.get(models.Channel, channel_in.id)
        if existing is not None:
            return existing
    if db.get(models.User, channel_in.user_id) is None:
        raise ValueError(f"user_id {channel_in.user_id} does not exist")
    channel = models.Channel(
        id=channel_in.id or uuid.uuid4(),
        user_id=channel_in.user_id,
        platform=channel_in.platform,
        handle=channel_in.handle,
        follower_count=channel_in.follower_count,
    )
    db.add(channel)
    db.flush()
    return channel


class DuplicateContentError(Exception):
    """A content row with this id already exists. Ingest creates content and never overwrites it."""


def create_content_with_metrics(db: Session, content_in: schemas.ContentIngest) -> tuple[models.Content, int]:
    if db.get(models.Channel, content_in.channel_id) is None:
        raise ValueError(f"channel_id {content_in.channel_id} does not exist")
    if content_in.id is not None and db.get(models.Content, content_in.id) is not None:
        raise DuplicateContentError(f"content {content_in.id} already exists")

    content = models.Content(
        id=content_in.id or uuid.uuid4(),
        channel_id=content_in.channel_id,
        content_type=content_in.content_type,
        title=content_in.title,
        caption=content_in.caption,
        hashtags=content_in.hashtags,
        topic_tags=content_in.topic_tags,
        hook_type=content_in.hook_type,
        duration_sec=content_in.duration_sec,
        posted_at=content_in.posted_at,
    )
    db.add(content)
    db.flush()

    metrics_created = 0
    for m in content_in.metrics:
        db.add(models.Metric(id=uuid.uuid4(), content_id=content.id, **m.model_dump(exclude={"captured_at"}), captured_at=m.captured_at))
        metrics_created += 1
    db.flush()

    return content, metrics_created

def upsert_user_baseline(
    db: Session,
    user_id: uuid.UUID,
    platform: str,
    content_type: str,
    rolling_median_perf: float,
    p25: float,
    p75: float,
) -> None:
    stmt = pg_insert(models.UserBaseline).values(
        user_id=user_id,
        platform=platform,
        content_type=content_type,
        rolling_median_perf=rolling_median_perf,
        p25=p25,
        p75=p75,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "platform", "content_type"],
        set_={
            "rolling_median_perf": stmt.excluded.rolling_median_perf,
            "p25": stmt.excluded.p25,
            "p75": stmt.excluded.p75,
            "updated_at": func.now(),
        },
    )
    db.execute(stmt)


def bulk_update_content_embeddings(db: Session, id_to_embedding: dict[uuid.UUID, list[float]]) -> None:
    for content_id, embedding in id_to_embedding.items():
        db.execute(
            update(models.Content).where(models.Content.id == content_id).values(caption_embedding=embedding)
        )    