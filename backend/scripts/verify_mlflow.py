import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import settings
import mlflow

mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
mlflow.set_experiment("week1-connectivity-check")

with mlflow.start_run(run_name="week1-smoke-test"):
    mlflow.log_param("checkpoint", "week1-mlflow-setup")
    mlflow.log_metric("check", 1)

print(f"Logged test run to MLflow at {settings.mlflow_tracking_uri}")