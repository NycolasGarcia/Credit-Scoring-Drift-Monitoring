"""Model lifecycle of the response: recalibration (A5), challenger (A6) with GR-7/GR-8.

Training data comes only from batches the contract approved (GR-7) and only from labels that
are already observable at decision time ``t`` (GR-8). The challenger reuses the champion's
recipe (``config/models/training.yaml``), so the comparison isolates the data, not the method.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel
from sklearn.linear_model import LogisticRegression

from src.config import PROJECT_ROOT
from src.data.features import model_feature_columns
from src.models.calibration import calibrate
from src.models.factory import build_model
from src.models.settings import load_training_config
from src.simulation.labels import logit

LIFECYCLE_PATH = PROJECT_ROOT / "config" / "response" / "lifecycle.yaml"


class LifecycleConfig(BaseModel):
    """Validated lifecycle file (sections kept as plain dicts of PROPOSTO values)."""

    version: int
    status: str
    recalibration: dict[str, Any]
    challenger: dict[str, Any]
    gate: dict[str, Any]
    registry: dict[str, Any]


def load_lifecycle(path: Path = LIFECYCLE_PATH) -> LifecycleConfig:
    """Load the lifecycle config."""
    with path.open(encoding="utf-8") as fh:
        return LifecycleConfig.model_validate(yaml.safe_load(fh))


class TrainingRefusedError(RuntimeError):
    """A guardrail refused to train (GR-7 or GR-8)."""


@dataclass
class BatchView:
    """What the lifecycle may read from one past batch."""

    index: int
    gate_status: str
    applications: pd.DataFrame
    scored: pd.DataFrame
    labels: pd.DataFrame


def training_rows(
    batches: list[BatchView], t: int, cfg: LifecycleConfig, window: int, min_rows: int
) -> pd.DataFrame:
    """Contract-approved rows (GR-7) of the last ``window`` mature cohorts at ``t`` (GR-8)."""
    accepted = cfg.challenger["accepted_gate_status"]
    parts = []
    for b in batches:
        if b.gate_status not in accepted:
            continue  # GR-7: never train on a batch the contract did not approve
        valid = b.applications[b.applications["loan_key"].isin(b.scored["loan_key"])]
        labels = b.labels[(b.labels["label_batch"] <= t) & b.labels["target"].notna()]
        parts.append(
            valid.merge(labels[["loan_key", "target"]], on="loan_key").assign(cohort=b.index)
        )
    parts = [p for p in parts if len(p)]
    if not parts:  # GR-8: nothing mature yet
        raise TrainingRefusedError(f"no mature, contract-approved labels at batch {t}")
    rows = pd.concat(parts, ignore_index=True)
    if len(rows):
        recent = sorted(rows["cohort"].unique())[-window:]
        rows = rows[rows["cohort"].isin(recent)]
    if len(rows) < min_rows:
        raise TrainingRefusedError(f"{len(rows)} mature, contract-approved rows < {min_rows}")
    return rows.sort_values("cohort", kind="stable").reset_index(drop=True)


def challenger_rows(batches: list[BatchView], t: int, cfg: LifecycleConfig) -> pd.DataFrame:
    """Training window of the challenger (A6)."""
    c = cfg.challenger
    return training_rows(batches, t, cfg, c["window_cohorts"], c["min_rows"])


def recalibration_rows(batches: list[BatchView], t: int, cfg: LifecycleConfig) -> pd.DataFrame:
    """Labels used to recalibrate (A5): the most recent mature cohorts only."""
    r = cfg.recalibration
    return training_rows(batches, t, cfg, r["window_cohorts"], r["min_labels"])


def split_window(rows: pd.DataFrame, cfg: LifecycleConfig) -> dict[str, pd.DataFrame]:
    """fit / calibration / evaluation by time: the most recent slice is kept for the gate."""
    n = len(rows)
    n_eval = int(n * cfg.challenger["evaluation_share"])
    n_cal = int(n * cfg.challenger["calibration_share"])
    cut_cal, cut_eval = n - n_eval - n_cal, n - n_eval
    return {"fit": rows.iloc[:cut_cal], "calibration": rows.iloc[cut_cal:cut_eval],
            "evaluation": rows.iloc[cut_eval:]}  # fmt: skip


def train_challenger(rows: pd.DataFrame, cfg: LifecycleConfig):
    """Champion recipe fitted and calibrated on the recent mature window."""
    tc = load_training_config()
    name = cfg.challenger["model"]
    parts = split_window(rows, cfg)
    model = build_model(name, tc.models[name], tc.seed, tc.log_features)
    x, y = parts["fit"][model_feature_columns()], parts["fit"]["target"].astype(int)
    model.fit(x, y)
    cal = parts["calibration"]
    return calibrate(model, cal[model_feature_columns()], cal["target"].astype(int),
                     cfg.challenger["calibration"]), parts["evaluation"]  # fmt: skip


class RecalibratedModel:
    """Champion with a Platt recalibration on its logit (A5): p' = sigmoid(a + b * logit(p))."""

    def __init__(self, base: Any, a: float, b: float) -> None:
        self.base, self.a, self.b = base, a, b

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        """Recalibrated default probability, as a two-column array like the champion's."""
        p = np.asarray(self.base.predict_proba(x)[:, 1], dtype=float)
        q = 1 / (1 + np.exp(-(self.a + self.b * logit(p))))
        return np.column_stack([1 - q, q])


def fit_recalibration(base: Any, rows: pd.DataFrame, cfg: LifecycleConfig) -> RecalibratedModel:
    """Fit (a, b) on mature labels; refuses when there are too few (GR-8)."""
    if len(rows) < cfg.recalibration["min_labels"]:
        raise TrainingRefusedError(f"{len(rows)} mature labels < {cfg.recalibration['min_labels']}")
    p = np.asarray(base.predict_proba(rows[model_feature_columns()])[:, 1], dtype=float)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(
        logit(p).reshape(-1, 1), rows["target"].astype(int)
    )
    return RecalibratedModel(base, float(lr.intercept_[0]), float(lr.coef_[0, 0]))
