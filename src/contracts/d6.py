"""D6 sweep: which share of a unit bug (annual -> monthly income) does each layer catch?

The contract (H10, batch median vs. reference) only sees gross bugs; the income PSI (L2 drift)
sees partial ones. The sweep makes the hand-off between the two layers measurable.
"""

from typing import Any

import numpy as np
import pandas as pd

from src.contracts.schema import reference_median
from src.contracts.settings import ContractConfig
from src.contracts.validate import validate_input
from src.monitoring.psi import psi_numeric

FRACTIONS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 1.0)
MONTHLY = 1 / 12


def corrupt_income(batch: pd.DataFrame, fraction: float, rng: np.random.Generator) -> pd.DataFrame:
    """Report a ``fraction`` of rows with monthly instead of annual income."""
    out = batch.copy()
    idx = rng.choice(out.index.to_numpy(), int(len(out) * fraction), replace=False)
    out.loc[idx, "annual_inc"] = out.loc[idx, "annual_inc"] * MONTHLY
    return out


def sweep(
    batch: pd.DataFrame, profile: dict[str, Any], cfg: ContractConfig, seed: int
) -> list[dict[str, Any]]:
    """Contract verdict and income PSI for each corrupted fraction (aggregates only)."""
    rng, ref_med, rows = np.random.default_rng(seed), reference_median(profile, "annual_inc"), []
    for frac in FRACTIONS:
        bad = corrupt_income(batch, frac, rng)
        result = validate_input(bad, profile, cfg)
        rows.append({
            "fraction_monthly": frac,
            "median_ratio": round(float(bad["annual_inc"].median() / ref_med), 4),
            "contract_status": result.status,
            "h10_triggered": "H10" in result.rule_counts,
            "annual_inc_psi": round(psi_numeric(batch["annual_inc"], bad["annual_inc"]), 4),
        })  # fmt: skip
    return rows
