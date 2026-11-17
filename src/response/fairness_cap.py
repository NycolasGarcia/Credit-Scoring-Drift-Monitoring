"""Fairness cap of the conservative mode (ADR-0015).

The conservative mode cuts by expected value with a single risk factor, which falls hardest on
groups that already score higher (renters, in this data). The cap gives back, inside each group
that ends up more than ``max_gap_pp`` below the best-approved group, the held applications with
the highest expected value, just enough to close the gap. Rows the champion itself rejects, the
kill switch and the quarantine are never touched.
"""

import math

import numpy as np
import pandas as pd

from src.governance.fairness import Segment, groups
from src.response.settings import FairnessCap


def approval_rates(approved: np.ndarray, groups: np.ndarray, min_rows: int) -> dict[str, float]:
    """Approval rate of every group with at least ``min_rows`` rows."""
    out = {}
    for g in np.unique(groups):
        mask = groups == g
        if mask.sum() >= min_rows:
            out[str(g)] = float(approved[mask].mean())
    return out


def relief(approved, held, value, groups, cap: FairnessCap) -> np.ndarray:
    """Held rows to approve so no group is more than the cap below the best one."""
    out = np.zeros(len(approved), bool)
    rates = approval_rates(approved, groups, cap.min_group_rows)
    if len(rates) < 2:
        return out
    floor = max(rates.values()) - cap.max_gap_pp / 100
    for g, rate in rates.items():
        mask = groups == g
        need = math.ceil(floor * mask.sum() - approved[mask].sum() - 1e-9)
        if rate >= floor or need <= 0:
            continue
        idx = np.flatnonzero(mask & held)
        out[idx[np.argsort(-value[idx], kind="stable")[:need]]] = True
    return out


def relieve(approved, held, value, frame: pd.DataFrame, cap: FairnessCap,
            segments: dict[str, Segment]) -> np.ndarray:  # fmt: skip
    """Held rows to approve so every capped segment fits the cap (a few passes over them)."""
    back = np.zeros(len(approved), bool)
    labels = {col: groups(frame, col, segments[col]).to_numpy() for col in cap.segments}
    for _ in range(cap.passes):
        for col in cap.segments:
            back |= relief(approved | back, held & ~back, value, labels[col], cap)
    return back
