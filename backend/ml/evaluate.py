"""Pure evaluation functions — no MLflow, no training. Kept separate so
metrics logic is independently testable, same split rationale as builder.py."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score

from ml import config as cfg


def classification_metrics(y_true: pd.Series, y_pred_proba: np.ndarray) -> dict:
    return {
        "roc_auc": float(roc_auc_score(y_true, y_pred_proba)),
        "pr_auc": float(average_precision_score(y_true, y_pred_proba)),
    }


def spearman_within_user(df: pd.DataFrame, actual_col: str, predicted_col: str,
                          min_rows: int = cfg.MIN_TEST_ROWS_FOR_SPEARMAN) -> float:
    """Mean of per-user Spearman rho, per §8.2 'within-user Spearman ρ'.
    Users with fewer than min_rows test points are excluded — a correlation
    on 1-2 points isn't meaningful."""
    rhos = []
    for _, group in df.groupby("user_id"):
        if len(group) < min_rows:
            continue
        rho, _ = spearmanr(group[actual_col], group[predicted_col])
        if not np.isnan(rho):
            rhos.append(rho)
    return float(np.mean(rhos)) if rhos else float("nan")