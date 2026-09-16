import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid

import numpy as np
import pytest

from ml.embedding_reduction import (
    fit_pca,
    transform_content_ids,
    transform_single_embedding,
)


def _make_embeddings(n, dim=384, seed=0):
    rng = np.random.default_rng(seed)
    ids = [str(uuid.uuid4()) for _ in range(n)]
    embeddings_map = {cid: rng.normal(size=dim) for cid in ids}
    return ids, embeddings_map


def test_fit_pca_depends_only_on_given_content_ids_not_full_map():
    """Core leakage guarantee: fitting must be identical whether or not
    test-split embeddings exist elsewhere in the same lookup map — mirrors
    how train_model.py calls this (passing train-only ids against the FULL
    embeddings_map, since _load_embeddings has no train/test concept itself)."""
    train_ids, train_map = _make_embeddings(20)
    extra_ids, extra_map = _make_embeddings(20, seed=99)
    full_map = {**train_map, **extra_map}

    pca_isolated = fit_pca(train_ids, train_map, n_components=5)
    pca_with_full_map_available = fit_pca(train_ids, full_map, n_components=5)

    np.testing.assert_allclose(pca_isolated.components_, pca_with_full_map_available.components_)


def test_transform_content_ids_produces_nan_for_missing_embedding():
    ids, embeddings_map = _make_embeddings(10)
    pca = fit_pca(ids, embeddings_map, n_components=4)

    ids_with_missing = ids + ["not-in-map"]
    result = transform_content_ids(pca, ids_with_missing, embeddings_map)

    assert result.shape == (11, 4)
    assert not np.isnan(result[:10]).any()
    assert np.isnan(result[10]).all()


def test_transform_single_embedding_matches_batch_transform():
    ids, embeddings_map = _make_embeddings(10)
    pca = fit_pca(ids, embeddings_map, n_components=4)

    single = transform_single_embedding(pca, embeddings_map[ids[0]])
    batch = transform_content_ids(pca, [ids[0]], embeddings_map)[0]

    np.testing.assert_allclose(single, batch)


def test_fit_pca_raises_on_no_valid_embeddings():
    with pytest.raises(ValueError):
        fit_pca(["missing-1", "missing-2"], {}, n_components=4)
