"""Champion finalization: cost threshold, importance, reference profile, registration."""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from src.models.dataset import xy
from src.models.evaluate import CandidateResult, score
from src.models.metrics import decision_metrics
from src.models.settings import CostConfig, TrainingConfig
from src.models.threshold import (
    best_f1_threshold,
    best_value_threshold,
    expected_value,
    loan_economics,
    threshold_grid,
)


def choose_threshold(model, calib: pd.DataFrame, cost: CostConfig) -> dict[str, float]:
    """Expected-value and F1 thresholds, both searched on the calibration set."""
    _, y = xy(calib)
    p = score(model, calib)
    gain, loss = loan_economics(calib, cost)
    grid = threshold_grid(cost)
    t_value, v_value = best_value_threshold(y.to_numpy(), p, gain, loss, grid)
    return {"threshold": t_value, "value_per_app_calib": v_value,
            "threshold_f1": best_f1_threshold(y.to_numpy(), p, grid)}  # fmt: skip


def decision_report(model, df: pd.DataFrame, thresholds: dict[str, float], cost: CostConfig):
    """Approval, bad rate among approved and value per application at each threshold."""
    _, y = xy(df)
    p, (gain, loss) = score(model, df), loan_economics(df, cost)
    report = {}
    for label in ("threshold", "threshold_f1"):
        t = thresholds[label]
        value = expected_value(y.to_numpy(), p, gain, loss, t)
        report[label] = {"threshold": t, **decision_metrics(y.to_numpy(), p, t)}
        report[label]["value_per_app"] = value
    return report


def feature_importance(model, test: pd.DataFrame, cfg: TrainingConfig) -> dict[str, float]:
    """Permutation importance (AUC drop) on a test sample, sorted descending."""
    sample = test.sample(min(cfg.importance.sample_rows, len(test)), random_state=cfg.seed)
    x, y = xy(sample)
    result = permutation_importance(
        model, x, y, scoring="roc_auc", n_repeats=cfg.importance.n_repeats,
        random_state=cfg.seed, n_jobs=1,
    )  # fmt: skip
    drops = dict(zip(x.columns, result.importances_mean, strict=True))
    return {k: float(v) for k, v in sorted(drops.items(), key=lambda kv: -kv[1])}


def profile_summary(
    champ: CandidateResult, held_out: pd.DataFrame, thresholds: dict[str, float],
    importance: dict[str, float], extra: dict[str, Any],
) -> dict[str, Any]:  # fmt: skip
    """Model-level fields of the reference profile."""
    p = score(champ.model, held_out)
    return {
        "model": {"name": champ.name, "calibration": champ.calibration, **extra},
        "threshold": thresholds["threshold"],
        "approval_rate": float(np.mean(p < thresholds["threshold"])),
        "expected_bad_rate": float(np.mean(p)),
        "observed_bad_rate": float(held_out["target"].mean()),
        "importance": importance,
        "importance_rank": list(importance),
        "reference_metrics": champ.metrics["test"],
    }
