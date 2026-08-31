"""
PCA reduction for caption embeddings (Week 5: "~32 dims to avoid
dominating tree splits"). Fit only on rows with a real embedding drawn from
the TRAIN split; content rows with no embedding (2 of ~2728, per Checkpoint 15
— manual test payloads with no caption) get NaN across all pca_* columns
rather than being dropped or imputed, matching how every other missing
numeric feature is already handled in this pipeline.
"""

import numpy as np
from sklearn.decomposition import PCA


def fit_pca(
    content_ids: list, embeddings_map: dict, n_components: int, random_state: int = 42
) -> PCA:
    """Fit PCA using ONLY the given content_ids' embeddings. Caller MUST pass
    train-split content_ids only (see scripts/train_model.py) — this function
    has no awareness of train/test itself, the caller's discipline is what
    guarantees no leakage."""
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
    """Transforms embeddings for the given content_ids using an ALREADY-FITTED
    pca object — never calls .fit(). Rows with no embedding get NaN."""
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
    """Transforms one embedding vector — used by idea_scoring.py for a single
    hypothetical idea's caption embedding. Never fits, only transforms."""
    return pca.transform(embedding.reshape(1, -1))[0]
