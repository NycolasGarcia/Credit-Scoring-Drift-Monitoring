"""Shared synthetic fixtures. Real data never enters the test suite."""

import numpy as np
import pandas as pd
import pytest

from src.data.target import is_mature, map_target

TEST_KEY = "unit-test-key-0123456789abcdef"


def synthetic_loans(n: int = 2_000, seed: int = 0) -> pd.DataFrame:
    """Processed-like frame (post-load) with the columns the split logic needs."""
    rng = np.random.default_rng(seed)
    months = pd.date_range("2012-06-01", "2015-12-01", freq="MS")
    issue_d = pd.Series(rng.choice(months, n))
    term = pd.Series(rng.choice([36.0, 60.0], n, p=[0.75, 0.25]))
    status = pd.Series(rng.choice(["Fully Paid", "Charged Off", "Current"], n, p=[0.7, 0.2, 0.1]))
    app = pd.Series(rng.choice(["Individual", "Joint App"], n, p=[0.95, 0.05]))
    return pd.DataFrame(
        {"id": [str(100_000 + i) for i in range(n)], "issue_d": issue_d, "term": term,
         "loan_status": status, "application_type": app}
    )  # fmt: skip


@pytest.fixture
def loans() -> pd.DataFrame:
    """Synthetic loans with target and maturity attached."""
    df = synthetic_loans()
    df["target"] = map_target(df["loan_status"])
    df["is_mature"] = is_mature(df["issue_d"], df["term"], pd.Timestamp("2019-03-01"))
    return df
