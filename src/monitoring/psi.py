"""Population Stability Index with bins fixed by the reference.

Bins come from reference quantiles (numeric) or reference levels (categorical) and are
stored in the reference profile; production never recomputes them. Missing values get
their own bin, unseen categories fall into ``__other__``, empty bins get ``EPS``.
"""

import numpy as np
import pandas as pd

EPS = 1e-4
NULL_BIN = "__null__"
OTHER_BIN = "__other__"


def quantile_edges(values: pd.Series, n_bins: int = 10) -> list[float]:
    """Interior cut points from reference quantiles (outer edges are -inf/+inf)."""
    clean = values.dropna().to_numpy(dtype=float)
    if clean.size == 0:
        return []
    qs = np.quantile(clean, np.linspace(0, 1, n_bins + 1)[1:-1])
    return [float(q) for q in np.unique(qs)]


def numeric_proportions(values: pd.Series, edges: list[float]) -> dict[str, float]:
    """Share of values per bin defined by ``edges``, plus the null bin."""
    full = np.concatenate([[-np.inf], edges, [np.inf]])
    clean = values.dropna().to_numpy(dtype=float)
    counts, _ = np.histogram(clean, bins=full)
    labels = [f"b{i}" for i in range(len(counts))]
    props = dict(zip(labels, counts / max(len(values), 1), strict=True))
    props[NULL_BIN] = float(values.isna().mean()) if len(values) else 0.0
    return {k: float(v) for k, v in props.items()}


def categorical_proportions(values: pd.Series, levels: list[str]) -> dict[str, float]:
    """Share per reference level, unseen levels pooled in ``__other__``, plus the null bin."""
    n = max(len(values), 1)
    known = values.where(values.isin(levels) | values.isna(), OTHER_BIN)
    counts = known.value_counts(dropna=False)
    props = {lvl: float(counts.get(lvl, 0) / n) for lvl in [*levels, OTHER_BIN]}
    props[NULL_BIN] = float(values.isna().sum() / n)
    return props


def psi_from_proportions(ref: dict[str, float], cur: dict[str, float]) -> float:
    """PSI = sum((cur - ref) * ln(cur / ref)) over the reference bins."""
    r = np.array([max(ref[k], EPS) for k in ref])
    c = np.array([max(cur.get(k, 0.0), EPS) for k in ref])
    return float(np.sum((c - r) * np.log(c / r)))


def psi_numeric(ref: pd.Series, cur: pd.Series, n_bins: int = 10) -> float:
    """Convenience PSI for two numeric samples (bins from ``ref``)."""
    edges = quantile_edges(ref, n_bins)
    return psi_from_proportions(numeric_proportions(ref, edges), numeric_proportions(cur, edges))
