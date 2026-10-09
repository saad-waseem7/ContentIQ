from functools import lru_cache
from typing import Optional

from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.crud import bulk_update_content_embeddings

# This model's 384-dimensional output matches the database vector column.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def build_embedding_text(title: Optional[str], caption: Optional[str]) -> str:
    parts = [p for p in (title, caption) if p]
    return " ".join(parts).strip()


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    # Normalize each caption so high-magnitude vectors do not dominate the winner centroid.
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    return vectors.tolist()


def fetch_content_needing_embeddings(db: Session, limit: Optional[int] = None):
    query = select(models.Content.id, models.Content.title, models.Content.caption).where(
        models.Content.caption_embedding.is_(None)
    )
    if limit is not None:
        query = query.limit(limit)
    return db.execute(query).all()


def embed_missing_content(db: Session, limit: Optional[int] = None) -> dict:
    rows = fetch_content_needing_embeddings(db, limit=limit)
    if not rows:
        return {"embedded": 0, "skipped_empty_text": 0}

    ids, texts, skipped = [], [], 0
    for content_id, title, caption in rows:
        text = build_embedding_text(title, caption)
        if not text:
            skipped += 1
            continue
        ids.append(content_id)
        texts.append(text)

    if texts:
        vectors = embed_texts(texts)
        bulk_update_content_embeddings(db, dict(zip(ids, vectors)))

    return {"embedded": len(ids), "skipped_empty_text": skipped}