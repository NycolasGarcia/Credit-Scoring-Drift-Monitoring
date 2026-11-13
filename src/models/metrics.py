"""Credit model metrics: ranking, calibration and decision quality."""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
    roc_curve,
)


def ks_statistic(y: np.ndarray, p: np.ndarray) -> float:
    """Credit KS: max separation between the score CDFs of bads and goods (= max |TPR - FPR|)."""
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(np.abs(tpr - fpr)))


def classification_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    """AUC, Gini, KS, PR-AUC, Brier, log-loss, observed and expected bad rate."""
    auc = float(roc_auc_score(y, p))
    return {
        "auc": auc,
        "gini": 2 * auc - 1,
        "ks": ks_statistic(y, p),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))),
        "bad_rate_observed": float(np.mean(y)),
        "bad_rate_expected": float(np.mean(p)),
    }


def decision_metrics(y: np.ndarray, p: np.ndarray, threshold: float) -> dict[str, float]:
    """Approval rate and bad rate among approved (approve when score < threshold)."""
    approved = p < threshold
    bad_approved = float(np.mean(y[approved])) if approved.any() else float("nan")
    return {"approval_rate": float(np.mean(approved)), "bad_rate_approved": bad_approved}


def calibration_table(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    """Observed vs. mean predicted bad rate per score decile."""
    bins = pd.qcut(p, q=n_bins, duplicates="drop")
    frame = pd.DataFrame({"y": y, "p": p, "bin": bins})
    table = frame.groupby("bin", observed=True).agg(
        n=("y", "size"), predicted=("p", "mean"), observed=("y", "mean")
    )
    return table.reset_index(drop=True)
