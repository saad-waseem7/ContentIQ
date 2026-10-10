"""Reduce caption embeddings with PCA fitted only on training rows.

Rows without embeddings remain NaN so they stay in the dataset and use the
same missing-value handling as other numeric features.
"""

import numpy as np
from sklearn.decomposition import PCA


def fit_pca(
    content_ids: list, embeddings_map: dict, n_components: int, random_state: int = 42
) -> PCA:
    """Fit PCA on the supplied IDs; callers must pass training IDs only to avoid leakage."""
    vectors = [embeddings_map[cid] for cid in content_ids if cid in embeddings_map]
    if not vectors:
        raise ValueError(
            "No embeddings available among the given content_ids to fit PCA."
        )
    matrix = np.stack(vectors)
    pca = PCA(n_components=n_components, random_state=random_state)
    pca.fit(matrix)
    return pca


def transform_content_ids(
    pca: PCA, content_ids: list, embeddings_map: dict
) -> np.ndarray:
    """Transform available embeddings with a fitted PCA model; leave missing rows as NaN."""
    n_components = pca.n_components_
    result = np.full((len(content_ids), n_components), np.nan)
    valid_positions = [i for i, cid in enumerate(content_ids) if cid in embeddings_map]
    if valid_positions:
        matrix = np.stack([embeddings_map[content_ids[i]] for i in valid_positions])
        transformed = pca.transform(matrix)
        for row_idx, pos in enumerate(valid_positions):
            result[pos] = transformed[row_idx]
    return result


def transform_single_embedding(pca: PCA, embedding: np.ndarray) -> np.ndarray:
    """Transform one candidate caption embedding without fitting PCA."""
    return pca.transform(embedding.reshape(1, -1))[0]
