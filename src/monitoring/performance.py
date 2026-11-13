"""L4 — performance with mature labels, respecting the label lag.

At monitoring time ``t`` the job evaluates exactly the labels that become observable at ``t``
(``label_batch == t``): simulated cohorts after ``label_lag`` batches, real loans at maturity.
"""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from src.models.metrics import ks_statistic
from src.simulation.labels import logit

QUINTILE_EDGES = (1, 3, 5, 7)  # p20, p40, p60, p80 among the reference decile edges
MIN_SEGMENT_ROWS = 200


def observable_at(history: pd.DataFrame, t: int) -> pd.DataFrame:
    """Scored rows whose label becomes observable at batch ``t``."""
    return history[(history["label_batch"] == t) & history["target"].notna()]


def cohort_metrics(y: np.ndarray, p: np.ndarray, reference_auc: float) -> dict[str, float]:
    """Ranking and calibration of one matured group."""
    auc = float(roc_auc_score(y, p))
    observed, expected = float(np.mean(y)), float(np.mean(p))
    return {"n_labeled": float(len(y)), "auc": auc, "auc_drop": reference_auc - auc,
            "ks": ks_statistic(y, p), "brier": float(brier_score_loss(y, p)),
            "bad_rate_observed": observed, "bad_rate_expected": expected,
            "bad_rate_ratio": observed / expected}  # fmt: skip


def _gap_by_quintile(frame: pd.DataFrame, feature: str, edges: list[float]) -> float | None:
    cuts = [edges[i] for i in QUINTILE_EDGES]
    groups = np.searchsorted(cuts, frame[feature].to_numpy(float), side="right")
    gaps = []
    for g in np.unique(groups[~frame[feature].isna().to_numpy()]):
        part = frame[groups == g]
        if len(part) >= MIN_SEGMENT_ROWS and 0 < part["target"].mean() < 1:
            gaps.append(float(logit(np.array([part["target"].mean()]))[0]
                              - logit(np.array([part["score"].mean()]))[0]))  # fmt: skip
    return max(gaps) - min(gaps) if len(gaps) >= 2 else None


def segment_gap(frame: pd.DataFrame, profile: dict[str, Any], top_k: int) -> tuple[float, str]:
    """Largest spread of the observed-vs-expected logit gap across quintiles of a top-k feature."""
    best, where = 0.0, ""
    for f in profile["importance_rank"][:top_k]:
        spec = profile["features"][f]
        if spec["type"] != "numeric" or len(spec["edges"]) < 9:
            continue
        gap = _gap_by_quintile(frame, f, spec["edges"])
        if gap is not None and gap > best:
            best, where = gap, f
    return best, where


def performance_signals(
    matured: pd.DataFrame, profile: dict[str, Any], top_k: int, min_rows: int
) -> dict[str, Any] | None:
    """L4 signals for the rows maturing now (None when too few or one class only)."""
    y = matured["target"].to_numpy(dtype=int)
    if len(y) < min_rows or y.min() == y.max():
        return None
    out: dict[str, Any] = cohort_metrics(y, matured["score"].to_numpy(float),
                                         profile["reference_metrics"]["auc"])  # fmt: skip
    out["segment_gap"], out["segment_feature"] = segment_gap(matured, profile, top_k)
    out["cohorts"] = sorted(int(c) for c in matured["cohort"].unique())
    return out
