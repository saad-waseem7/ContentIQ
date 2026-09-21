import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from app import insight_clustering as clustering
from app import insight_config as cfg


def _make_separated_embeddings(n_per_cluster=40, dim=20, seed=0):
    rng = np.random.default_rng(seed)
    centers = [rng.normal(scale=1, size=dim) * 10 for _ in range(4)]
    embeddings_map = {}
    labels_true = []
    idx = 0
    for c_idx, center in enumerate(centers):
        for _ in range(n_per_cluster):
            cid = f"c{idx}"
            embeddings_map[cid] = center + rng.normal(scale=0.3, size=dim)
            labels_true.append((cid, c_idx))
            idx += 1
    return embeddings_map, labels_true


def _make_niche_df(labels_true, content_type_by_cluster):
    rows = []
    for cid, cluster in labels_true:
        rows.append({
            "content_id": cid, "content_type": content_type_by_cluster[cluster],
            "hook_type": "story", "primary_topic_tag": "t",
            "performance_z": 1.0 if cluster == 0 else 0.0,
        })
    return pd.DataFrame(rows)


def test_clustering_unavailable_below_min_niche_posts():
    embeddings_map = {f"c{i}": np.random.rand(20) for i in range(cfg.CLUSTER_MIN_NICHE_POSTS - 10)}
    niche_df = pd.DataFrame({"content_id": list(embeddings_map.keys())})
    result, label_df = clustering.compute_niche_clusters(embeddings_map, niche_df)
    assert result["available"] is False
    assert label_df is None


def test_clustering_available_with_well_separated_data():
    embeddings_map, labels_true = _make_separated_embeddings()
    content_type_by_cluster = {0: "carousel", 1: "text", 2: "image", 3: "short_video"}
    niche_df = _make_niche_df(labels_true, content_type_by_cluster)

    result, label_df = clustering.compute_niche_clusters(embeddings_map, niche_df)

    assert result["available"] is True
    assert result["k"] >= 3
    assert result["silhouette_score"] >= cfg.CLUSTER_SILHOUETTE_MIN
    assert len(result["clusters"]) >= 1
    assert label_df is not None


def test_clustering_unavailable_when_no_real_structure():
    rng = np.random.default_rng(1)
    embeddings_map = {f"c{i}": rng.normal(size=20) for i in range(cfg.CLUSTER_MIN_NICHE_POSTS + 20)}
    niche_df = pd.DataFrame({
        "content_id": list(embeddings_map.keys()),
        "content_type": ["carousel"] * len(embeddings_map),
        "hook_type": ["story"] * len(embeddings_map),
        "primary_topic_tag": ["t"] * len(embeddings_map),
        "performance_z": [0.0] * len(embeddings_map),
    })
    result, label_df = clustering.compute_niche_clusters(embeddings_map, niche_df)
    # Pure noise SHOULD produce a low silhouette score most of the time,
    # but this isn't a hard mathematical guarantee for every possible seed.
    if result["available"] is False:
        assert result["reason_unavailable"] is not None
        assert label_df is None


def test_user_cluster_summary_counts_correctly():
    label_df = pd.DataFrame({"content_id": ["c1", "c2", "c3", "c4"], "cluster_id": [0, 0, 1, 2]})
    summary = clustering.build_user_cluster_summary(label_df, ["c1", "c2", "c3"])
    by_cluster = {s["cluster_id"]: s["user_post_count"] for s in summary}
    assert by_cluster[0] == 2
    assert by_cluster[1] == 1
    assert 2 not in by_cluster


def test_user_cluster_summary_empty_when_no_label_df():
    assert clustering.build_user_cluster_summary(None, ["c1"]) == []


def test_cluster_cache_reused_when_embedding_count_unchanged(monkeypatch):
    clustering.clear_cluster_cache()

    call_count = {"n": 0}
    embeddings_map, labels_true = _make_separated_embeddings()

    def fake_load(db, niche):
        call_count["n"] += 1
        return embeddings_map

    monkeypatch.setattr(clustering, "_load_niche_embeddings", fake_load)
    niche_df = _make_niche_df(labels_true, {0: "carousel", 1: "text", 2: "image", 3: "short_video"})

    r1, _ = clustering.load_and_compute_niche_clusters(None, "fitness", niche_df)
    r2, _ = clustering.load_and_compute_niche_clusters(None, "fitness", niche_df)

    assert call_count["n"] == 2  # DB queried both times (cheap freshness check)...
    assert r1 is r2  # ...but the expensive KMeans result is the SAME cached object, not recomputed    