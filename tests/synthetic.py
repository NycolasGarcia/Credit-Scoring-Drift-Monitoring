"""Synthetic application batches with the real schema. Real data never enters the test suite."""

import numpy as np
import pandas as pd

from src.contracts.schema import application_columns
from src.data.features import model_feature_columns

LEVELS = {"grade": list("ABCDEFG"), "home_ownership": ["MORTGAGE", "OWN", "RENT"],
          "verification_status": ["Not Verified", "Source Verified", "Verified"],
          "purpose": ["credit_card", "debt_consolidation", "other"]}  # fmt: skip


def synthetic_batch(n: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Valid application batch with the real schema and plausible values."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.uniform(1, 30, n) for c in model_feature_columns()})
    df["loan_amnt"] = rng.uniform(1000, 35000, n).round(0)
    df["term"] = rng.choice([36, 60], n).astype("int64")
    df["int_rate"] = rng.uniform(6, 25, n)
    r = df["int_rate"] / 1200
    df["installment"] = df["loan_amnt"] * r / (1 - (1 + r) ** (-df["term"]))
    df["annual_inc"] = rng.lognormal(11, 0.5, n)
    df["fico_range_low"] = rng.integers(660, 800, n).astype(float)
    df["emp_length"] = rng.integers(0, 11, n).astype(float)
    for col, levels in LEVELS.items():
        df[col] = rng.choice(levels, n)
    df["loan_key"] = [f"k{i:06d}" for i in range(n)]
    df["issue_d"] = pd.Timestamp("2013-06-01")
    df["addr_state"] = rng.choice(["CA", "NY", "TX"], n)
    return df[application_columns()]
