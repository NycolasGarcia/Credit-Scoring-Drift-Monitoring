"""Group metrics for the bias analysis (pure): approval, equal opportunity, calibration, gaps.

Outcome convention: ``target`` = 1 is a default. "Good approval rate" is P(approve | good), the
equal-opportunity quantity for applicants who would repay; "bad approval rate" is
P(approve | default). Gaps are max - min over groups with at least ``min_group_size`` rows.
"""

from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel
from sklearn.metrics import roc_auc_score

from src.config import PROJECT_ROOT

FAIRNESS_PATH = PROJECT_ROOT / "config" / "governance" / "fairness.yaml"
GAP_METRICS = ("approval_rate", "good_approval_rate", "calibration_ratio")


class Segment(BaseModel):
    """How a column becomes groups."""

    kind: Literal["category", "bands"]
    edges: list[float] | None = None


class Alert(BaseModel):
    """Increase of the approval gap that raises a fairness signal (§8.4, PROPOSTO)."""

    sev1_gap_increase_pp: float
    sev2_gap_increase_pp: float


class FairnessConfig(BaseModel):
    """Whole fairness file."""

    version: int
    status: str
    segments: dict[str, Segment]
    min_group_size: int
    min_batch_group_rows: int
    scenarios: list[str]
    alert: Alert


def load_fairness(path: Path = FAIRNESS_PATH) -> FairnessConfig:
    """Load and validate the fairness YAML."""
    with path.open(encoding="utf-8") as fh:
        return FairnessConfig.model_validate(yaml.safe_load(fh))


def _band(v: float, edges: list[float]) -> str:
    if pd.isna(v):
        return "desconhecido"
    lo = max([e for e in edges if e <= v], default=None)
    hi = min([e for e in edges if e > v], default=None)
    return f"{lo:g}+" if hi is None else f"{0 if lo is None else lo:g}-{hi:g}"


def groups(frame: pd.DataFrame, column: str, seg: Segment) -> pd.Series:
    """Group label per row for one segment column."""
    if seg.kind == "bands":
        return frame[column].map(lambda v: _band(v, seg.edges or []))
    return frame[column].astype("string").fillna("desconhecido")


def _auc(y: np.ndarray, s: np.ndarray) -> float | None:
    return float(roc_auc_score(y, s)) if len(np.unique(y)) == 2 else None


def group_metrics(y: np.ndarray, score: np.ndarray, approved: np.ndarray) -> dict[str, Any]:
    """Metrics of one group."""
    good, bad = y == 0, y == 1
    return {"n": len(y), "approval_rate": float(approved.mean()),
            "good_approval_rate": float(approved[good].mean()) if good.any() else None,
            "bad_approval_rate": float(approved[bad].mean()) if bad.any() else None,
            "bad_rate": float(y.mean()), "expected_bad_rate": float(score.mean()),
            "calibration_ratio": float(y.mean() / score.mean()), "auc": _auc(y, score)}  # fmt: skip


def segment_table(frame: pd.DataFrame, approved: np.ndarray, column: str, seg: Segment):
    """One row per group of a segment; ``frame`` carries ``target`` and ``score``."""
    labels = groups(frame, column, seg).to_numpy()
    y, s = frame["target"].to_numpy(int), frame["score"].to_numpy(float)
    return {str(g): group_metrics(y[labels == g], s[labels == g], approved[labels == g])
            for g in sorted(set(labels))}  # fmt: skip


def gaps(table: dict[str, dict[str, Any]], min_size: int) -> dict[str, float | None]:
    """max - min of each gap metric over groups large enough to compare."""
    big = [m for m in table.values() if m["n"] >= min_size]
    out: dict[str, float | None] = {}
    for k in GAP_METRICS:
        vals = [m[k] for m in big if m[k] is not None]
        out[k] = float(max(vals) - min(vals)) if len(vals) >= 2 else None
    return out


def approval_gap(approved: np.ndarray, labels: np.ndarray, min_rows: int) -> float | None:
    """max - min approval rate over groups with at least ``min_rows`` rows."""
    rates = [
        approved[labels == g].mean() for g in np.unique(labels) if (labels == g).sum() >= min_rows
    ]
    return float(max(rates) - min(rates)) if len(rates) >= 2 else None


def fairness_drift(frame: pd.DataFrame, policy: np.ndarray, champion: np.ndarray, cfg) -> dict:
    """Per segment: approval gap of the policy, of the plain champion and the increase (p.p.)."""
    segs = {}
    for col, seg in cfg.segments.items():
        labels = groups(frame, col, seg).to_numpy()
        p, c = (approval_gap(a, labels, cfg.min_batch_group_rows) for a in (policy, champion))
        inc = None if p is None or c is None else 100 * (p - c)
        segs[col] = {"policy_pp": None if p is None else 100 * p,
                     "champion_pp": None if c is None else 100 * c, "increase_pp": inc}  # fmt: skip
    worst = max(
        (s["increase_pp"] for s in segs.values() if s["increase_pp"] is not None), default=0
    )
    a = cfg.alert
    level = 2 if worst > a.sev2_gap_increase_pp else 1 if worst > a.sev1_gap_increase_pp else 0
    return {"segments": segs, "max_increase_pp": worst, "level": level}


def cramers_v(a: pd.Series, b: pd.Series) -> float:
    """Association between two categorical columns (0 = none, 1 = one determines the other)."""
    table = pd.crosstab(a, b).to_numpy(float)
    n = table.sum()
    expected = table.sum(1, keepdims=True) @ table.sum(0, keepdims=True) / n
    chi2 = float(((table - expected) ** 2 / np.where(expected == 0, 1, expected)).sum())
    k = min(table.shape) - 1
    return float(np.sqrt(chi2 / (n * k))) if k > 0 else 0.0


def proxy_strength(frame: pd.DataFrame, features: list[str], column: str) -> dict[str, float]:
    """Cramér's V between ``column`` and each model feature (numeric ones in deciles)."""
    out = {}
    for f in features:
        x = frame[f]
        if pd.api.types.is_numeric_dtype(x):
            x = pd.qcut(x.rank(method="first"), 10, labels=False)
        out[f] = cramers_v(x.astype("string").fillna("nulo"), frame[column].astype("string"))
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
