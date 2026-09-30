import hashlib
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow

from app.config import settings
from ml import config as cfg
from ml.artifact_io import atomic_path
from ml.data_prep import (
    content_type_average_baseline,
    load_labeled_feature_table,
    prepare_model_matrix,
    temporal_train_test_split,
)
from ml.evaluate import classification_metrics, spearman_within_user
from ml.models import train_classifier, train_regressor
from ml.shap_analysis import compute_shap_values, global_feature_importance, planted_signal_shap_check

FEATURES_PATH = Path(__file__).resolve().parents[1] / "data" / "features.parquet"
MODEL_ARTIFACT_PATH = Path(__file__).resolve().parents[1] / "data" / "classifier.joblib"
CATEGORY_LEVELS_PATH = Path(__file__).resolve().parents[1] / "data" / "category_levels.json"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    df = load_labeled_feature_table(str(FEATURES_PATH))
    data_hash = file_sha256(FEATURES_PATH)

    X_full = prepare_model_matrix(df)
    train_df, test_df = temporal_train_test_split(df)
    X_train, X_test = X_full.loc[train_df.index], X_full.loc[test_df.index]

    y_class_train = train_df[cfg.CLASSIFIER_TARGET].astype(int)
    y_class_test = test_df[cfg.CLASSIFIER_TARGET].astype(int)
    y_reg_train = train_df[cfg.REGRESSOR_TARGET]
    y_reg_test = test_df[cfg.REGRESSOR_TARGET]

    classifier = train_classifier(X_train, y_class_train)
    regressor = train_regressor(X_train, y_reg_train)

    category_levels = {col: X_full[col].cat.categories.tolist() for col in cfg.CATEGORICAL_FEATURES}
    # Levels are written before the model. A reader that lands between the two replaces
    # sees (old model, new levels), which is safe when a retrain adds categories: the old
    # model already treats them as unknown. The reverse order would score a category the
    # new model knows as missing. (A retrain that removes a category has the opposite risk.)
    with atomic_path(CATEGORY_LEVELS_PATH) as tmp_path:
        tmp_path.write_text(json.dumps(category_levels))
    with atomic_path(MODEL_ARTIFACT_PATH) as tmp_path:
        joblib.dump(classifier, tmp_path)
    print(f"Saved category levels to {CATEGORY_LEVELS_PATH}")
    print(f"Saved classifier to {MODEL_ARTIFACT_PATH}")

    class_proba = classifier.predict_proba(X_test)[:, 1]
    reg_pred = regressor.predict(X_test)

    model_class_metrics = classification_metrics(y_class_test, class_proba)
    reg_eval_df = test_df[["user_id"]].copy()
    reg_eval_df["actual"] = y_reg_test.values
    reg_eval_df["predicted"] = reg_pred
    model_spearman = spearman_within_user(reg_eval_df, "actual", "predicted")

    baseline_class_pred = content_type_average_baseline(train_df, test_df, cfg.CLASSIFIER_TARGET)
    baseline_reg_pred = content_type_average_baseline(train_df, test_df, cfg.REGRESSOR_TARGET)
    baseline_class_metrics = classification_metrics(y_class_test, baseline_class_pred)
    baseline_reg_eval_df = test_df[["user_id"]].copy()
    baseline_reg_eval_df["actual"] = y_reg_test.values
    baseline_reg_eval_df["predicted"] = baseline_reg_pred.values
    baseline_spearman = spearman_within_user(baseline_reg_eval_df, "actual", "predicted")

    shap_values = compute_shap_values(classifier, X_test)
    importance_df = global_feature_importance(shap_values, list(X_test.columns))
    signal_check_df = planted_signal_shap_check(shap_values, X_test, test_df, cfg.PLANTED_SIGNAL)

    importance_path = Path("/tmp/shap_feature_importance.csv")
    importance_df.to_csv(importance_path, index=False)

    fig, ax = plt.subplots(figsize=(8, 6))
    top15 = importance_df.head(15)
    ax.barh(top15["feature"][::-1], top15["mean_abs_shap"][::-1])
    ax.set_xlabel("mean |SHAP value|")
    ax.set_title("Top 15 feature importances (classifier)")
    plt.tight_layout()
    shap_plot_path = Path("/tmp/shap_importance.png")
    fig.savefig(shap_plot_path)
    plt.close(fig)

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(cfg.MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run(run_name="week4-lightgbm-baseline"):
        mlflow.log_param("data_snapshot_hash", data_hash)
        mlflow.log_param("n_train_rows", len(train_df))
        mlflow.log_param("n_test_rows", len(test_df))
        mlflow.log_params({f"clf_{k}": v for k, v in cfg.LGBM_CLASSIFIER_PARAMS.items()})
        mlflow.log_params({f"reg_{k}": v for k, v in cfg.LGBM_REGRESSOR_PARAMS.items()})

        mlflow.log_metric("classifier_roc_auc", model_class_metrics["roc_auc"])
        mlflow.log_metric("classifier_pr_auc", model_class_metrics["pr_auc"])
        mlflow.log_metric("classifier_baseline_roc_auc", baseline_class_metrics["roc_auc"])
        mlflow.log_metric("regressor_spearman_rho", model_spearman)
        mlflow.log_metric("regressor_baseline_spearman_rho", baseline_spearman)

        mlflow.lightgbm.log_model(classifier, artifact_path="classifier")
        mlflow.lightgbm.log_model(regressor, artifact_path="regressor")

        summary = {
            "classifier": model_class_metrics,
            "classifier_baseline": baseline_class_metrics,
            "regressor_spearman": model_spearman,
            "regressor_baseline_spearman": baseline_spearman,
        }
        summary_path = Path("/tmp/week4_summary.json")
        summary_path.write_text(json.dumps(summary, indent=2))
        mlflow.log_artifact(str(summary_path))
        mlflow.log_artifact(str(importance_path))
        mlflow.log_artifact(str(shap_plot_path))

    print("\n=== Week 4 acceptance check ===")
    print(f"ROC-AUC: {model_class_metrics['roc_auc']:.4f} (need >= {cfg.ROC_AUC_THRESHOLD}) -> "
          f"{'PASS' if model_class_metrics['roc_auc'] >= cfg.ROC_AUC_THRESHOLD else 'FAIL'}")
    print(f"Spearman rho: {model_spearman:.4f} (need >= {cfg.SPEARMAN_THRESHOLD}) -> "
          f"{'PASS' if model_spearman >= cfg.SPEARMAN_THRESHOLD else 'FAIL'}")
    print(f"Beats baseline ROC-AUC ({baseline_class_metrics['roc_auc']:.4f}): "
          f"{'PASS' if model_class_metrics['roc_auc'] > baseline_class_metrics['roc_auc'] else 'FAIL'}")
    print(f"Beats baseline Spearman ({baseline_spearman:.4f}): "
          f"{'PASS' if model_spearman > baseline_spearman else 'FAIL'}")
    print("\n=== SHAP: top 10 features ===")
    print(importance_df.head(10).to_string(index=False))

    print("\n=== SHAP: planted signal recovery check ===")
    print(signal_check_df.to_string(index=False))

    signal_recovered = bool(
        (signal_check_df["topic_shap_match"] > signal_check_df["topic_shap_non_match"]).all()
        and (signal_check_df["hook_shap_match"] > signal_check_df["hook_shap_non_match"]).all()
    )
    print(f"\nPlanted signal recovered in ALL {len(signal_check_df)} niches (topic + hook SHAP both higher for matches): "f"{'PASS' if signal_recovered else 'FAIL'}")


if __name__ == "__main__":
    main()