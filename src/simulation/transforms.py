"""Scenario transforms (Strategy per kind) and the intensity schedule.

Three families, applied in this order:
    real   (scale, shift)  -> the world changed; labels follow the reference P(Y|X).
    bug    (unit_bug)      -> only the observed data changed; labels stay untouched.
    label  (logit_shift)   -> P(Y|X) changed; X is untouched.
"""

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from src.contracts.schema import amortized_installment
from src.simulation.settings import LogitShift, Scale, Schedule, Shift, Transform, UnitBug

AMORTIZATION_INPUTS = frozenset({"loan_amnt", "int_rate", "term"})


def intensity(schedule: Schedule, t: int) -> float:
    """Share of the configured magnitude applied at batch ``t`` (0 = none, 1 = full)."""
    if schedule.shape == "none" or t < schedule.onset:
        return 0.0
    elapsed = t - schedule.onset
    if schedule.shape == "gradual":
        return min(1.0, (elapsed + 1) / schedule.ramp)
    if schedule.shape == "recurrent":
        return 1.0 if elapsed % schedule.period < schedule.period / 2 else 0.0
    return 1.0


def _scale(values: pd.Series, tr: Scale, level: float) -> pd.Series:
    return values * (1 + (tr.factor - 1) * level)


def _shift(values: pd.Series, tr: Shift, level: float) -> pd.Series:
    return values + tr.delta * level


REAL: dict[type, Callable[[pd.Series, Any, float], pd.Series]] = {Scale: _scale, Shift: _shift}


def apply_real(df: pd.DataFrame, transforms: list[Transform], level: float) -> pd.DataFrame:
    """Apply real-world changes; keep the installment coherent with amount, rate and term."""
    out, touched = df.copy(), set()
    for tr in transforms:
        if type(tr) in REAL and level > 0:
            out[tr.feature] = REAL[type(tr)](out[tr.feature], tr, level)
            touched.add(tr.feature)
    if touched & AMORTIZATION_INPUTS:
        out["installment"] = amortized_installment(out)
    return out


def apply_bugs(
    df: pd.DataFrame, transforms: list[Transform], level: float, rng: np.random.Generator
) -> tuple[pd.DataFrame, np.ndarray]:
    """Corrupt the observed data; return it and the mask of corrupted rows."""
    out, hit = df.copy(), np.zeros(len(df), dtype=bool)
    for tr in transforms:
        if isinstance(tr, UnitBug) and level > 0:
            rows = rng.random(len(out)) < tr.fraction * level
            out.loc[rows, tr.feature] = out.loc[rows, tr.feature] / tr.divisor
            hit |= rows
    return out, hit


def segment_threshold(tr: LogitShift, profile: dict[str, Any]) -> float | None:
    """Reference decile edge that opens the affected segment (None = everyone)."""
    if tr.segment is None:
        return None
    return float(profile["features"][tr.segment.feature]["edges"][tr.segment.edge_index])


def logit_delta(
    df: pd.DataFrame, transforms: list[Transform], level: float, profile: dict[str, Any]
) -> np.ndarray:
    """Per-row shift of the default logit implied by the label transforms."""
    delta = np.zeros(len(df))
    for tr in transforms:
        if not isinstance(tr, LogitShift):
            continue
        edge = segment_threshold(tr, profile)
        mask = np.ones(len(df), bool) if edge is None else (df[tr.segment.feature] >= edge)
        delta += tr.delta * level * np.asarray(mask, dtype=float)
    return delta


def drifted_features(transforms: list[Transform]) -> list[str]:
    """Features whose observed distribution the scenario changes (ground truth for L2)."""
    return sorted({tr.feature for tr in transforms if isinstance(tr, Scale | Shift | UnitBug)})
