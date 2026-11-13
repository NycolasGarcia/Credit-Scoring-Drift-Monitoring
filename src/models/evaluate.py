"""Candidate evaluation across sets and champion selection (ADR-0006)."""

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score

from src.models.dataset import xy
from src.models.metrics import classification_metrics
from src.models.settings import TrainingConfig
from src.monitoring.psi import psi_numeric


@dataclass
class CandidateResult:
    """Everything produced for one candidate model."""

    name: str
    run_id: str
    model: Any
    calibration: str
    briers: dict[str, float]
    metrics: dict[str, dict[str, float]] = field(default_factory=dict)
    score_psi: dict[str, float] = field(default_factory=dict)
    model_uri: str = ""


def cv_auc(model, x: pd.DataFrame, y: pd.Series, cfg: TrainingConfig) -> dict[str, float]:
    """Stratified k-fold AUC on the training set (mean and std)."""
    folds = StratifiedKFold(n_splits=cfg.cv_folds, shuffle=True, random_state=cfg.seed)
    scores = cross_val_score(model, x, y, cv=folds, scoring="roc_auc", n_jobs=1)
    return {"auc": float(np.mean(scores)), "auc_std": float(np.std(scores))}


def score(model, df: pd.DataFrame) -> np.ndarray:
    """Probability of default for each row."""
    x, _ = xy(df)
    return np.asarray(model.predict_proba(x)[:, 1])


def evaluate_sets(model, sets: dict[str, pd.DataFrame]) -> dict[str, dict[str, float]]:
    """Classification metrics on each named labeled set."""
    out = {}
    for name, df in sets.items():
        _, y = xy(df)
        out[name] = {**classification_metrics(y.to_numpy(), score(model, df)), "n": len(df)}
    return out


def score_stability(model, base: pd.DataFrame, others: dict[str, pd.DataFrame]) -> dict[str, float]:
    """PSI of the score distribution of each set against ``base`` (bins from ``base``)."""
    ref = pd.Series(score(model, base))
    return {name: psi_numeric(ref, pd.Series(score(model, df))) for name, df in others.items()}


def select_champion(candidates: list[CandidateResult], cfg: TrainingConfig) -> CandidateResult:
    """Best test AUC; within the tie tolerance, the most stable score (lowest OOT PSI).

    Raises:
        ValueError: if any non-baseline candidate fails to beat the dummy on test AUC.
    """
    dummy = next(c for c in candidates if c.name == "dummy")
    real = [c for c in candidates if c.name != "dummy"]
    losers = [c.name for c in real if c.metrics["test"]["auc"] <= dummy.metrics["test"]["auc"]]
    if losers:
        raise ValueError(f"candidates do not beat the dummy baseline: {losers}")
    top_auc = max(c.metrics["test"]["auc"] for c in real)
    tied = [
        c for c in real if top_auc - c.metrics["test"]["auc"] <= cfg.selection.auc_tie_tolerance
    ]
    return min(tied, key=lambda c: max(c.score_psi.values(), default=0.0))
