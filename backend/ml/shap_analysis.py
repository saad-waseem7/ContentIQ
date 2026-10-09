"""Explain classifier predictions with TreeSHAP on held-out test rows."""
import warnings

import numpy as np
import pandas as pd
import shap


def compute_shap_values(model, X_test: pd.DataFrame) -> np.ndarray:
    explainer = shap.TreeExplainer(model)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        shap_values = explainer.shap_values(X_test)
    if isinstance(shap_values, list):  # some shap/lightgbm version combos return [class0, class1]
        shap_values = shap_values[1]
    return shap_values

def global_feature_importance(shap_values: np.ndarray, feature_names: list[str]) -> pd.DataFrame:
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    return (
        pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs_shap})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )


def planted_signal_shap_check(
    shap_values: np.ndarray, X_test: pd.DataFrame, test_df: pd.DataFrame, planted_signal: dict
) -> pd.DataFrame:
    """Compare mean topic and hook SHAP values for matching and non-matching rows per niche."""
    topic_idx = list(X_test.columns).index("primary_topic_tag")
    hook_idx = list(X_test.columns).index("hook_type")

    rows = []
    for niche, sig in planted_signal.items():
        niche_mask = (test_df["niche"] == niche).values
        match_mask = niche_mask & (test_df["hook_type"] == sig["hook_type"]).values & \
                     (X_test["primary_topic_tag"] == sig["topic_tag"]).values
        non_match_mask = niche_mask & ~match_mask

        if match_mask.sum() == 0 or non_match_mask.sum() == 0:
            continue

        rows.append({
            "niche": niche,
            "n_matches_in_test": int(match_mask.sum()),
            "topic_shap_match": float(shap_values[match_mask, topic_idx].mean()),
            "topic_shap_non_match": float(shap_values[non_match_mask, topic_idx].mean()),
            "hook_shap_match": float(shap_values[match_mask, hook_idx].mean()),
            "hook_shap_non_match": float(shap_values[non_match_mask, hook_idx].mean()),
        })
    return pd.DataFrame(rows)