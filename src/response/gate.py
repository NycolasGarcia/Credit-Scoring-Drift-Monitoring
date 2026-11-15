"""Promotion gate (GR-5): a challenger replaces the champion only if every check passes.

1. beats the champion on the recent mature window (AUC);
2. does not lose more than δ of AUC on the 2013 reference test;
3. is calibrated on the recent window, or at least not worse than the champion (ADR-0020);
4. does not widen the approval-rate gap between groups (fairness proxy until F8).
"""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src.data.features import model_feature_columns
from src.response.lifecycle import LifecycleConfig

MIN_GROUP_ROWS = 200


def scores(model: Any, df: pd.DataFrame) -> np.ndarray:
    """Default probability of every row."""
    return np.asarray(model.predict_proba(df[model_feature_columns()])[:, 1], dtype=float)


def approval_gap_pp(df: pd.DataFrame, p: np.ndarray, threshold: float, segment: str) -> float:
    """Largest difference in approval rate between groups with enough rows, in p.p."""
    approved = pd.Series(p < threshold, index=df.index)
    groups = approved.groupby(df[segment]).agg(["mean", "size"])
    rates = groups.loc[groups["size"] >= MIN_GROUP_ROWS, "mean"]
    return float((rates.max() - rates.min()) * 100) if len(rates) > 1 else 0.0


def _check(value: float, limit: float, passed: bool) -> dict[str, Any]:
    return {"value": round(value, 6), "limit": limit, "passed": bool(passed)}


def evaluate_gate(
    champion: Any, challenger: Any, recent: pd.DataFrame, reference: pd.DataFrame,
    threshold: float, cfg: LifecycleConfig,
) -> dict[str, Any]:  # fmt: skip
    """Every GR-5 check, its value, its limit and the overall verdict."""
    g, y = cfg.gate, recent["target"].astype(int).to_numpy()
    pc, pk = scores(champion, recent), scores(challenger, recent)
    gain = roc_auc_score(y, pk) - roc_auc_score(y, pc)
    yr = reference["target"].astype(int).to_numpy()
    loss = roc_auc_score(yr, scores(champion, reference)) - roc_auc_score(
        yr, scores(challenger, reference)
    )
    calib = abs(pk.mean() - y.mean()) * 100
    calib_champion = abs(pc.mean() - y.mean()) * 100
    seg = g["fairness_segment"]
    fair = approval_gap_pp(recent, pk, threshold, seg) - approval_gap_pp(recent, pc, threshold, seg)
    lim_gain, lim_loss = g["min_auc_gain_recent"], g["max_auc_loss_reference"]
    # ADR-0020: calibrated, or at least not worse calibrated than the champion it replaces
    lim_cal = max(g["max_calibration_gap_pp"], calib_champion)
    checks = {
        "auc_gain_recent": _check(gain, lim_gain, gain > lim_gain),
        "auc_loss_reference": _check(loss, lim_loss, loss <= lim_loss),
        "calibration_gap_pp": _check(calib, lim_cal, calib <= lim_cal),
        "fairness_gap_increase_pp": _check(fair, g["max_fairness_gap_increase_pp"],
                                           fair <= g["max_fairness_gap_increase_pp"]),
    }  # fmt: skip
    return {"passed": all(c["passed"] for c in checks.values()), "checks": checks,
            "rows_recent": len(recent), "rows_reference": len(reference)}  # fmt: skip
