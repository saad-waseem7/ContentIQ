"""Prepare labeled feature rows for LightGBM training.

Keep splitting and leakage exclusions separate from model fitting so they
can be tested without training a model.
"""
import pandas as pd

from ml import config as cfg


def load_labeled_feature_table(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    before = len(df)
    df = df.dropna(subset=[cfg.CLASSIFIER_TARGET, cfg.REGRESSOR_TARGET]).copy()
    print(f"Dropped {before - len(df)} rows with insufficient group history (no valid label).")
    return df


def temporal_train_test_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split each user's timeline independently because their posting dates differ."""
    train_parts, test_parts = [], []
    for _, group in df.sort_values("posted_at").groupby("user_id", sort=False):
        n_test = max(1, int(len(group) * cfg.TEST_FRACTION_PER_USER))
        train_parts.append(group.iloc[:-n_test])
        test_parts.append(group.iloc[-n_test:])
    return pd.concat(train_parts), pd.concat(test_parts)


def prepare_model_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Selects ONLY leakage-safe feature columns, sets pandas 'category' dtype
    for LightGBM's native categorical handling."""
    df = df.copy()
    df["primary_topic_tag"] = df["topic_tags"].apply(lambda tags: tags[0] if tags is not None and len(tags) > 0 else "none")

    X = df[cfg.CATEGORICAL_FEATURES + cfg.NUMERIC_FEATURES].copy()
    for col in cfg.CATEGORICAL_FEATURES:
        X[col] = X[col].astype("category")
    for col in ("has_cta", "is_weekend", "is_first_post_for_user"):
        X[col] = X[col].astype(int)
    return X


def content_type_average_baseline(train_df: pd.DataFrame, test_df: pd.DataFrame, target_col: str) -> pd.Series:
    ct_means = train_df.groupby("content_type")[target_col].mean()
    global_mean = train_df[target_col].mean()
    result = test_df["content_type"].map(ct_means).fillna(global_mean)
    return result.astype(float)