"""Optional PCA-on-embeddings experiment, separate from default training.

PCA is fit on training-split content IDs and saved under data/experiments,
separate from the default classifier artifacts.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import joblib
import pandas as pd

from app.database import SessionLocal
from features.builder import _load_embeddings
from ml import config as cfg
from ml.data_prep import load_labeled_feature_table, prepare_model_matrix, temporal_train_test_split
from ml.embedding_reduction import fit_pca, transform_content_ids
from ml.evaluate import classification_metrics, spearman_within_user
from ml.models import train_classifier, train_regressor

FEATURES_PATH = Path(__file__).resolve().parents[1] / "data" / "features.parquet"
EXPERIMENT_DIR = Path(__file__).resolve().parents[1] / "data" / "experiments"
PCA_COMPONENTS = 32  # PRD's own stated figure, not tuned


def main():
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_labeled_feature_table(str(FEATURES_PATH))
    X_full = prepare_model_matrix(df)
    train_df, test_df = temporal_train_test_split(df)

    db = SessionLocal()
    try:
        embeddings_map = _load_embeddings(db)
    finally:
        db.close()
    embeddings_map = {str(k): v for k, v in embeddings_map.items()}

    train_content_ids = df.loc[train_df.index, "content_id"].tolist()
    pca = fit_pca(train_content_ids, embeddings_map, n_components=PCA_COMPONENTS)
    pca_matrix = transform_content_ids(pca, df["content_id"].tolist(), embeddings_map)
    pca_df = pd.DataFrame(pca_matrix, columns=[f"pca_{i}" for i in range(PCA_COMPONENTS)], index=df.index)
    X_full = pd.concat([X_full, pca_df], axis=1)

    joblib.dump(pca, EXPERIMENT_DIR / "pca.joblib")
    print(f"Explained variance ratio (sum of {PCA_COMPONENTS}): {pca.explained_variance_ratio_.sum():.4f}")

    X_train, X_test = X_full.loc[train_df.index], X_full.loc[test_df.index]
    y_class_train, y_class_test = train_df[cfg.CLASSIFIER_TARGET].astype(int), test_df[cfg.CLASSIFIER_TARGET].astype(int)
    y_reg_train, y_reg_test = train_df[cfg.REGRESSOR_TARGET], test_df[cfg.REGRESSOR_TARGET]

    classifier = train_classifier(X_train, y_class_train)
    regressor = train_regressor(X_train, y_reg_train)

    class_proba = classifier.predict_proba(X_test)[:, 1]
    reg_pred = regressor.predict(X_test)
    class_metrics = classification_metrics(y_class_test, class_proba)

    reg_eval_df = test_df[["user_id"]].copy()
    reg_eval_df["actual"], reg_eval_df["predicted"] = y_reg_test.values, reg_pred
    spearman = spearman_within_user(reg_eval_df, "actual", "predicted")

    print(f"\n[EXPERIMENT ONLY, NOT SHIPPED] ROC-AUC: {class_metrics['roc_auc']:.4f}, Spearman: {spearman:.4f}")


if __name__ == "__main__":
    main()