import warnings

import numpy as np
import pandas as pd
from scipy.stats import ConstantInputWarning, spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score

from ml import config as cfg


def classification_metrics(y_true: pd.Series, y_pred_proba: np.ndarray) -> dict:
    return {
        "roc_auc": float(roc_auc_score(y_true, y_pred_proba)),
        "pr_auc": float(average_precision_score(y_true, y_pred_proba)),
    }


def spearman_within_user(
    df: pd.DataFrame,
    actual_col: str,
    predicted_col: str,
    min_rows: int = cfg.MIN_TEST_ROWS_FOR_SPEARMAN,
) -> float:
    """Average per-user Spearman rho, excluding small groups and undefined correlations."""
    rhos = []
    for _, group in df.groupby("user_id"):
        if len(group) < min_rows:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ConstantInputWarning)
            rho, _ = spearmanr(group[actual_col], group[predicted_col])
        if not np.isnan(rho):
            rhos.append(rho)
    return float(np.mean(rhos)) if rhos else float("nan")
