"""L3 — output drift: score distribution, approval rate and expected bad rate per batch."""

from typing import Any

import pandas as pd

from src.monitoring.psi import numeric_proportions, psi_from_proportions


def score_psi(scores: pd.Series, profile: dict[str, Any]) -> float:
    """PSI of the score against the reference score deciles in the profile."""
    spec = profile["score"]
    return psi_from_proportions(spec["ref_props"], numeric_proportions(scores, spec["edges"]))


def output_signals(scored: pd.DataFrame, profile: dict[str, Any]) -> dict[str, float | None]:
    """Score PSI, approval rate (and its change in p.p.) and expected bad rate."""
    if scored.empty:
        return {"score_psi": None, "approval_rate": None, "approval_delta_pp": None,
                "expected_bad_rate": None}  # fmt: skip
    approval = float((scored["decision"] == "approve").mean())
    return {
        "score_psi": score_psi(scored["score"], profile),
        "approval_rate": approval,
        "approval_delta_pp": (approval - profile["approval_rate"]) * 100,
        "expected_bad_rate": float(scored["score"].mean()),
    }
