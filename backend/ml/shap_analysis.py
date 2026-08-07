"""
SHAP explainability for the Week 4 classifier — PRD's interpretability
requirement and its explicit acceptance line: "model recovers the planted
signal." TreeExplainer, not KernelExplainer — exact and fast for
gradient-boosted trees, the standard choice for this model family.

Computed on the held-out TEST set only, consistent with why the eval split
exists: an explanation should reflect data the model didn't fit on.
"""
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
    """Per niche: mean SHAP contribution of primary_topic_tag and hook_type,
    comparing planted-match rows vs non-match rows in the SAME niche. A model
    that actually recovered the signal should show a clearly larger positive
    contribution for matches on both columns."""
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