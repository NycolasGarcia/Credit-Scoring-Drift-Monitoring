"""Severity engine (§8.4): signal values -> SEV level per signal and per batch.

0 = quiet, 1 = attention, 2 = probable degradation, 3 = critical. Every cut point comes from
``config/monitoring/thresholds.yaml``.
"""

from typing import Any

import pandas as pd

from src.monitoring.settings import MonitoringConfig, Threshold

ALERTING = ("feature_psi", "score_psi", "approval_delta_pp", "bad_rate_ratio", "auc_drop")


def magnitude(value: float, th: Threshold) -> float:
    """Value oriented so that larger means worse, per the threshold's direction."""
    if th.direction == "two_sided":
        return abs(value)
    if th.direction == "symmetric_ratio":
        return max(value, 1 / value) if value > 0 else float("inf")
    return value


def level(value: float | None, th: Threshold) -> int:
    """Highest severity whose cut point the oriented value reaches."""
    if value is None:
        return 0
    v = magnitude(value, th)
    for sev, cut in ((3, th.sev3), (2, th.sev2), (1, th.sev1)):
        if cut is not None and v >= cut:
            return sev
    return 0


def feature_level(table: pd.DataFrame, th: Threshold, top_k: int) -> tuple[int, list[str]]:
    """L2 level: any feature >= sev1; top-k feature >= sev2; >= N top-k features >= sev2."""
    flagged = table.loc[table["psi"] >= th.sev1, "feature"].tolist()
    top = table[table["importance_rank"] <= top_k]
    n_high = int((top["psi"] >= th.sev2).sum())
    if th.sev3_min_features and n_high >= th.sev3_min_features:
        return 3, flagged
    if n_high:
        return 2, flagged
    return (1 if flagged else 0), flagged


def batch_severity(
    table: pd.DataFrame,
    l3: dict[str, Any],
    l4: dict[str, Any] | None,
    cfg: MonitoringConfig,
) -> dict[str, Any]:
    """Per-signal levels, overall batch level and the features that crossed sev1."""
    feat, flagged = feature_level(table, cfg.get("feature_psi"), cfg.top_k_features)
    values = {**l3, **(l4 or {})}
    signals = {"feature_psi": feat}
    for name in ALERTING[1:]:
        signals[name] = level(values.get(name), cfg.get(name))
    return {"signals": signals, "level": max(signals.values()), "flagged_features": flagged}
