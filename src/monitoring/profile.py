"""Reference profile: the training-time snapshot the monitoring job compares against.

Monitoring never recomputes the reference: bins, score distribution, expected bad rate,
approval rate and feature importance all come from this artifact.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.features import CATEGORICAL_FEATURES, model_feature_columns
from src.monitoring.psi import (
    categorical_proportions,
    numeric_proportions,
    quantile_edges,
)

PROFILE_VERSION = 1
N_BINS = 10


def feature_profile(values: pd.Series, categorical: bool) -> dict[str, Any]:
    """Bins and reference proportions for one feature."""
    if categorical:
        levels = sorted(values.dropna().astype(str).unique().tolist())
        return {"type": "categorical", "levels": levels,
                "ref_props": categorical_proportions(values.astype("string"), levels)}  # fmt: skip
    edges = quantile_edges(values, N_BINS)
    return {"type": "numeric", "edges": edges, "ref_props": numeric_proportions(values, edges)}


def score_profile(scores: pd.Series) -> dict[str, Any]:
    """Score bins (reference deciles) and proportions."""
    edges = quantile_edges(scores, N_BINS)
    return {"edges": edges, "ref_props": numeric_proportions(scores, edges)}


def build_profile(
    reference: pd.DataFrame, scores: pd.Series, summary: dict[str, Any]
) -> dict[str, Any]:
    """Assemble the profile from reference features, held-out scores and model summary."""
    features = {
        col: feature_profile(reference[col], col in CATEGORICAL_FEATURES)
        for col in model_feature_columns()
    }
    return {"profile_version": PROFILE_VERSION, **summary,
            "features": features, "score": score_profile(scores)}  # fmt: skip


def write_profile(profile: dict[str, Any], path: Path) -> Path:
    """Persist the profile as pretty JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
