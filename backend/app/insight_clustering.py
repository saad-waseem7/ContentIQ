"""
Week 6 topic clustering — KMeans over caption embeddings, scoped to a
SINGLE NICHE's population, not per-user: at 150-200 posts, a per-user
clustering would be too thin to be stable, and topic vocabulary is
inherently niche-specific anyway, making niche-level pooling the more
defensible statistical unit.

Split into a pure function (compute_niche_clusters, no DB access) and a
thin DB-loading wrapper — same pattern as features/builder.py's
compute_feature_table vs build_feature_table split, kept here for the
same reason: the pure function is directly unit-testable.

Deliberately NOT using an LLM to label clusters — each cluster is
described by its own deterministic majority content_type/hook_type/topic,
computed from the same rows that were clustered.
"""
import threading
from collections import Counter
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import insight_config as cfg
from app import models

# Cached by niche. The entry is valid only while BOTH inputs are unchanged: the number of
# embedded posts in Postgres (new content was ingested) and a fingerprint of the feature rows
# the cluster statistics are computed from (features.parquet was rebuilt). Checking costs one
# COUNT query; the embeddings themselves are loaded only on a miss. What is worth caching is
# the KMeans sweep (up to 4 k-values x n_init=10 = up to 40 fits).
_cluster_cache: dict[str, tuple[tuple, dict, Optional[pd.DataFrame]]] = {}
_cluster_cache_lock = threading.Lock()


def clear_cluster_cache() -> None:
    """Clear cached clusters so tests can exercise a fresh computation."""
    with _cluster_cache_lock:
        _cluster_cache.clear()


def _count_niche_embeddings(db: Session, niche: str) -> int:
    return db.execute(
        select(func.count())
        .select_from(models.Content)
        .join(models.Channel, models.Content.channel_id == models.Channel.id)
        .join(models.User, models.Channel.user_id == models.User.id)
        .where(models.User.niche == niche)
        .where(models.Content.caption_embedding.is_not(None))
    ).scalar_one()


def _feature_fingerprint(niche_df: pd.DataFrame) -> tuple:
    """Cheap identity of the feature rows behind the cluster statistics."""
    if niche_df.empty:
        return (0, 0, 0.0)
    ids = int(pd.util.hash_pandas_object(niche_df["content_id"], index=False).sum())
    return (len(niche_df), ids, round(float(niche_df["performance_z"].sum()), 6))


def _load_niche_embeddings(db: Session, niche: str) -> dict:
    rows = db.execute(
        select(models.Content.id, models.Content.caption_embedding)
        .join(models.Channel, models.Content.channel_id == models.Channel.id)
        .join(models.User, models.Channel.user_id == models.User.id)
        .where(models.User.niche == niche)
        .where(models.Content.caption_embedding.is_not(None))
    ).all()
    return {str(cid): np.array(vec, dtype=float) for cid, vec in rows}


def _choose_k(matrix: np.ndarray):
    best_k, best_score, best_labels = None, -1.0, None
    for k in cfg.CLUSTER_K_RANGE:
        if k >= len(matrix):
            continue
        km = KMeans(n_clusters=k, random_state=cfg.CLUSTER_RANDOM_STATE, n_init=10)
        labels = km.fit_predict(matrix)
        try:
            score = silhouette_score(matrix, labels)
        except ValueError:
            continue
        if score > best_score:
            best_k, best_score, best_labels = k, score, labels
    return best_k, best_score, best_labels


def _dominant_value(series: pd.Series) -> str:
    counts = Counter(series.dropna())
    return counts.most_common(1)[0][0] if counts else "unknown"


def compute_niche_clusters(embeddings_map: dict, niche_df_valid_with_topic: pd.DataFrame) -> tuple[dict, Optional[pd.DataFrame]]:
    """Cluster supplied embeddings without database access or caching."""
    if len(embeddings_map) < cfg.CLUSTER_MIN_NICHE_POSTS:
        return {"available": False, "reason_unavailable": "Not enough content in this niche to cluster reliably."}, None

    content_ids = list(embeddings_map.keys())
    matrix = np.stack([embeddings_map[cid] for cid in content_ids])
    best_k, best_score, labels = _choose_k(matrix)

    if best_k is None or best_score < cfg.CLUSTER_SILHOUETTE_MIN:
        return {
            "available": False,
            "reason_unavailable": "No sufficiently distinct topic clusters were found in this niche's content.",
            "silhouette_score": round(float(best_score), 3) if best_score > -1 else None,
        }, None

    label_df = pd.DataFrame({"content_id": content_ids, "cluster_id": labels})
    merged = label_df.merge(niche_df_valid_with_topic, on="content_id", how="inner")

    clusters = []
    for cluster_id, group in merged.groupby("cluster_id"):
        if len(group) < cfg.CLUSTER_MIN_SAMPLES_PER_CLUSTER:
            continue
        clusters.append({
            "cluster_id": int(cluster_id),
            "n": int(len(group)),
            "mean_performance_z": round(float(group["performance_z"].mean()), 3),
            "dominant_content_type": _dominant_value(group["content_type"]),
            "dominant_hook_type": _dominant_value(group["hook_type"]),
            "dominant_topic_tag": _dominant_value(group["primary_topic_tag"]),
            "is_high_performing": bool(group["performance_z"].mean() > 0.5),
        })
    clusters.sort(key=lambda c: c["mean_performance_z"], reverse=True)

    return {
        "available": True, "reason_unavailable": None,
        "k": int(best_k), "silhouette_score": round(float(best_score), 3),
        "clusters": clusters,
    }, label_df


def load_and_compute_niche_clusters(db: Session, niche: str, niche_df_valid_with_topic: pd.DataFrame):
    version = (_count_niche_embeddings(db, niche), _feature_fingerprint(niche_df_valid_with_topic))

    with _cluster_cache_lock:
        cached = _cluster_cache.get(niche)
        if cached is not None and cached[0] == version:
            return cached[1], cached[2]

    embeddings_map = _load_niche_embeddings(db, niche)
    result, label_df = compute_niche_clusters(embeddings_map, niche_df_valid_with_topic)

    with _cluster_cache_lock:
        _cluster_cache[niche] = (version, result, label_df)
    return result, label_df


def build_user_cluster_summary(label_df: Optional[pd.DataFrame], user_content_ids: list) -> list[dict]:
    if label_df is None:
        return []
    user_labels = label_df[label_df["content_id"].isin(user_content_ids)]
    if user_labels.empty:
        return []
    counts = user_labels["cluster_id"].value_counts()
    return [{"cluster_id": int(cid), "user_post_count": int(n)} for cid, n in counts.items()]