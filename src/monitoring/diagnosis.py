"""Diagnosis (§8.7): which degradation type best explains a batch's signals.

Order follows the decision tree: data/pipeline first (D0, D6), then labeled performance
(D3 vs D2), then input drift (D1) and output-only drift (D4).
"""

from typing import Any

import numpy as np
import pandas as pd

from src.monitoring.drift import feature_psi
from src.monitoring.settings import DiagnosisParams, MonitoringConfig


def unit_bug_signature(
    ref: pd.Series, cur: pd.Series, spec: dict[str, Any], params: DiagnosisParams
) -> dict[str, Any] | None:
    """Unit-bug evidence: an excess low tail that, rescaled by a unit factor, looks normal again."""
    cut = float(np.nanquantile(ref.to_numpy(float), params.tail_quantile))
    tail = (cur < cut).to_numpy()
    excess = float(tail.mean()) - params.tail_quantile
    if excess < params.min_tail_excess:
        return None
    base = feature_psi(cur, spec)
    fixed = {f: feature_psi(cur.where(~tail, cur * f), spec) for f in params.unit_factors}
    factor = min(fixed, key=fixed.get)
    if fixed[factor] > params.max_psi_ratio * base:
        return None
    return {"factor": factor, "tail_excess": excess, "psi": base, "psi_corrected": fixed[factor]}


def unit_bugs(
    reference: pd.DataFrame,
    batch: pd.DataFrame,
    table: pd.DataFrame,
    profile: dict[str, Any],
    cfg: MonitoringConfig,
) -> dict[str, dict[str, Any]]:
    """Unit-bug signatures among numeric features that crossed the L2 attention level."""
    sev1 = cfg.get("feature_psi").sev1
    candidates = table[(table["type"] == "numeric") & (table["psi"] >= sev1)]["feature"]
    found = {f: unit_bug_signature(reference[f], batch[f], profile["features"][f], cfg.diagnosis)
             for f in candidates}  # fmt: skip
    return {f: sig for f, sig in found.items() if sig is not None}


def labeled_diagnosis(
    signals: dict[str, int], l4: dict[str, Any] | None, cfg: MonitoringConfig
) -> str | None:
    """D3 (ranking lost or miscalibration concentrated in a segment) vs. D2 (uniform shift)."""
    if l4 is None:
        return None
    if signals["auc_drop"] >= 1:
        return "D3"
    if signals["bad_rate_ratio"] >= 1:
        return "D3" if l4["segment_gap"] >= cfg.get("segment_gap").sev1 else "D2"
    return None


def diagnose(
    gate_status: str,
    severity: dict[str, Any],
    l4: dict[str, Any] | None,
    bugs: dict[str, Any],
    cfg: MonitoringConfig,
) -> str:
    """Degradation code for one batch (``none`` when nothing fires)."""
    s = severity["signals"]
    if gate_status == "blocked":
        return "D0"
    if bugs:
        return "D6"
    labeled = labeled_diagnosis(s, l4, cfg)
    if labeled:
        return labeled
    if s["feature_psi"] >= 1:
        return "D1"
    return "D4" if s["score_psi"] >= 1 or s["approval_delta_pp"] >= 1 else "none"
