"""MLflow tracking and Model Registry client (aliases champion / challenger)."""

import os

import mlflow
from mlflow import MlflowClient

from src.config import PROJECT_ROOT, get_settings

ARTIFACT_ROOT = PROJECT_ROOT / "mlruns" / "artifacts"
CHAMPION = "champion"


def setup_tracking(experiment: str) -> str:
    """Point MLflow at the project store and return the experiment id (created if missing)."""
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    (PROJECT_ROOT / "mlruns").mkdir(exist_ok=True)
    mlflow.set_tracking_uri(get_settings().mlflow_tracking_uri)
    found = mlflow.get_experiment_by_name(experiment)
    if found is not None:
        exp_id = found.experiment_id
    else:
        exp_id = mlflow.create_experiment(experiment, artifact_location=ARTIFACT_ROOT.as_uri())
    mlflow.set_experiment(experiment_id=exp_id)
    return exp_id


def register_champion(model_uri: str, model_name: str) -> str:
    """Register a logged model and point the ``champion`` alias at the new version."""
    version = mlflow.register_model(model_uri, model_name).version
    MlflowClient().set_registered_model_alias(model_name, CHAMPION, str(version))
    return str(version)


def load_alias(model_name: str, alias: str = CHAMPION):
    """Load the model currently behind ``alias``."""
    return mlflow.sklearn.load_model(f"models:/{model_name}@{alias}")
