"""Threshold calibration on the control population (S0 bootstrap, §8.8, caixa 5.6).

Each replicate is an A/A batch drawn from the holdout (same population as the reference).
The null distribution of every signal gives its false-alarm rate at any cut point. The rule:

    sev1 = max(proposed, null quantile 1 - target_sev1 / n_signals)   (Bonferroni over signals)
    sev2 = max(proposed, just above the null maximum)                   (0% SEV-2 in control)
    sev3 = max(proposed, sev2)
"""

import math
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src.monitoring.performance import segment_gap
from src.monitoring.psi import EPS
from src.monitoring.settings import MonitoringConfig
from src.monitoring.severity import ALERTING, magnitude

STEP = {"feature_psi": 0.01, "score_psi": 0.01, "approval_delta_pp": 0.1,
        "bad_rate_ratio": 0.01, "auc_drop": 0.005, "segment_gap": 0.05}  # fmt: skip


def bin_codes(values: pd.Series, spec: dict[str, Any]) -> np.ndarray:
    """Bin index of every row, in the key order of ``spec['ref_props']`` (null bin last)."""
    if spec["type"] == "categorical":
        lookup = {lvl: i for i, lvl in enumerate(spec["levels"])}
        other, null = len(spec["levels"]), len(spec["levels"]) + 1
        mapped = values.astype("string").map(lambda v: lookup.get(v, other))
        return np.where(values.isna(), null, mapped.fillna(null)).astype(int)
    codes = np.searchsorted(spec["edges"], values.to_numpy(float), side="right")
    return np.where(values.isna(), len(spec["edges"]) + 1, codes).astype(int)


def psi_codes(codes: np.ndarray, ref: np.ndarray) -> float:
    """PSI of a sample of bin codes against reference proportions (same EPS rule)."""
    cur = np.bincount(codes, minlength=len(ref)) / len(codes)
    r, c = np.maximum(ref, EPS), np.maximum(cur, EPS)
    return float(np.sum((c - r) * np.log(c / r)))


def _replicate(idx: np.ndarray, ctx: dict[str, Any]) -> dict[str, float]:
    psis = {f: psi_codes(c[idx], ctx["ref"][f]) for f, c in ctx["codes"].items()}
    y, p = ctx["y"][idx], ctx["scores"][idx]
    frame = ctx["frame"].iloc[idx]
    return {
        "feature_psi": max(psis.values()),
        "feature_psi_top": max(psis[f] for f in ctx["top"]),
        "score_psi": psi_codes(ctx["score_codes"][idx], ctx["score_ref"]),
        "approval_delta_pp": (np.mean(p < ctx["threshold"]) - ctx["approval"]) * 100,
        "bad_rate_ratio": float(np.mean(y) / np.mean(p)),
        "auc_drop": ctx["auc"] - float(roc_auc_score(y, p)),
        "segment_gap": segment_gap(frame, ctx["profile"], ctx["top_k"])[0],
    }  # fmt: skip


def bootstrap_null(
    holdout: pd.DataFrame, scores: np.ndarray, profile: dict[str, Any], cfg: MonitoringConfig
) -> pd.DataFrame:
    """One row per A/A replicate with the value of every signal."""
    feats = profile["features"]
    ctx = {"codes": {f: bin_codes(holdout[f], s) for f, s in feats.items()},
           "ref": {f: np.array(list(s["ref_props"].values())) for f, s in feats.items()},
           "top": profile["importance_rank"][: cfg.top_k_features],
           "score_codes": bin_codes(pd.Series(scores), {"type": "numeric", **profile["score"]}),
           "score_ref": np.array(list(profile["score"]["ref_props"].values())),
           "y": holdout["target"].to_numpy(int), "scores": scores,
           "frame": holdout.assign(score=scores), "profile": profile, "top_k": cfg.top_k_features,
           "threshold": profile["threshold"], "approval": profile["approval_rate"],
           "auc": profile["reference_metrics"]["auc"]}  # fmt: skip
    rng, p = np.random.default_rng(cfg.calibration.seed), cfg.calibration
    rows = [_replicate(rng.choice(len(holdout), p.batch_size, replace=False), ctx)
            for _ in range(p.replicates)]  # fmt: skip
    return pd.DataFrame(rows)


def _ceil(x: float, step: float) -> float:
    return round(math.ceil(x / step - 1e-9) * step, 6)


def _above(x: float, step: float) -> float:
    return round((math.floor(x / step + 1e-9) + 1) * step, 6)


def calibrate_signal(null: pd.DataFrame, signal: str, cfg: MonitoringConfig) -> dict[str, Any]:
    """Null summary, false alarm at the proposed cut and the calibrated cut points."""
    th, step = cfg.get(signal), STEP[signal]
    s1 = null[signal].map(lambda v: magnitude(v, th))
    s2 = null["feature_psi_top"] if signal == "feature_psi" else s1
    # segment_gap is diagnostic only (D3 vs D2): calibrated strictly at 1%
    alpha = 0.01 if signal == "segment_gap" else cfg.false_alarm_target.sev1 / len(ALERTING)
    out = {"signal": signal, "id": th.id, "q50": float(s1.median()),
           "q95": float(s1.quantile(0.95)), "q99": float(s1.quantile(0.99)), "max": float(s1.max()),
           "proposed": {"sev1": th.sev1, "sev2": th.sev2, "sev3": th.sev3},
           "fa_proposed_sev1": float((s1 >= th.sev1).mean()),
           "sev1": max(th.sev1, _ceil(float(s1.quantile(1 - alpha)), step))}  # fmt: skip
    if th.sev2 is not None:
        out["fa_proposed_sev2"] = float((s2 >= th.sev2).mean())
        out["sev2"] = max(th.sev2, _above(float(s2.max()), step))
    if th.sev3 is not None:
        out["sev3"] = max(th.sev3, out["sev2"])
    return out


def composite_false_alarm(
    null: pd.DataFrame, cuts: dict[str, dict[str, Any]], cfg: MonitoringConfig
) -> dict[str, float]:
    """Share of control replicates with batch severity >= 1 and >= 2 under the given cuts."""
    any1 = np.zeros(len(null), bool)
    any2 = np.zeros(len(null), bool)
    for signal in ALERTING:
        th, c = cfg.get(signal), cuts[signal]
        v = null[signal].map(lambda x, th=th: magnitude(x, th))
        top = null["feature_psi_top"] if signal == "feature_psi" else v
        any1 |= (v >= c["sev1"]).to_numpy()
        if c.get("sev2") is not None:
            any2 |= (top >= c["sev2"]).to_numpy()
    return {"sev1_plus": float(any1.mean()), "sev2_plus": float(any2.mean())}
