"""L2 — input drift per feature: PSI (gate), KS / chi-square (recorded), Wasserstein (effect).

PSI uses the bins frozen in the reference profile. KS, chi-square and the normalized
Wasserstein distance compare against the reference sample. p-values are recorded but never
trigger alerts: with thousands of rows every irrelevant difference is "significant" (NV-10).
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from src.monitoring.psi import (
    OTHER_BIN,
    categorical_proportions,
    numeric_proportions,
    psi_from_proportions,
)


def feature_psi(values: pd.Series, spec: dict[str, Any]) -> float:
    """PSI of one feature against the reference profile bins (null bin included)."""
    if spec["type"] == "categorical":
        cur = categorical_proportions(values.astype("string"), spec["levels"])
    else:
        cur = numeric_proportions(values, spec["edges"])
    return psi_from_proportions(spec["ref_props"], cur)


def wasserstein_norm(ref: pd.Series, cur: pd.Series) -> float:
    """First Wasserstein distance divided by the reference std (same formula as Evidently)."""
    r, c = ref.dropna().to_numpy(float), cur.dropna().to_numpy(float)
    return float(stats.wasserstein_distance(r, c) / max(float(np.std(r)), 0.001))


def ks_test(ref: pd.Series, cur: pd.Series) -> tuple[float, float]:
    """Two-sample KS statistic D and p-value (non-null values)."""
    res = stats.ks_2samp(ref.dropna(), cur.dropna())
    return float(res.statistic), float(res.pvalue)


def chi2_test(ref: pd.Series, cur: pd.Series, levels: list[str]) -> float:
    """p-value of the chi-square test of homogeneity over reference levels + other."""

    def counts(s: pd.Series) -> np.ndarray:
        known = s.dropna().astype(str).where(lambda x: x.isin(levels), OTHER_BIN)
        return known.value_counts().reindex([*levels, OTHER_BIN], fill_value=0).to_numpy()

    table = np.vstack([counts(ref), counts(cur)])
    table = table[:, table.sum(axis=0) > 0]
    return float(stats.chi2_contingency(table)[1])


def feature_row(name: str, ref: pd.Series, cur: pd.Series, spec: dict[str, Any]) -> dict:
    """All L2 statistics of one feature."""
    row: dict[str, Any] = {"feature": name, "type": spec["type"], "psi": feature_psi(cur, spec)}
    if spec["type"] == "categorical":
        row.update(ks_d=None, ks_p=None, wasserstein=None,
                   chi2_p=chi2_test(ref, cur, spec["levels"]))  # fmt: skip
        return row
    d, p = ks_test(ref, cur)
    row.update(ks_d=d, ks_p=p, wasserstein=wasserstein_norm(ref, cur), chi2_p=None)
    return row


def drift_table(
    reference: pd.DataFrame, batch: pd.DataFrame, profile: dict[str, Any]
) -> pd.DataFrame:
    """One row per model feature, with its importance rank (1 = most important)."""
    rank = {f: i + 1 for i, f in enumerate(profile["importance_rank"])}
    rows = [feature_row(f, reference[f], batch[f], spec)
            for f, spec in profile["features"].items()]  # fmt: skip
    out = pd.DataFrame(rows)
    out["importance_rank"] = out["feature"].map(rank)
    return out.sort_values("psi", ascending=False).reset_index(drop=True)
