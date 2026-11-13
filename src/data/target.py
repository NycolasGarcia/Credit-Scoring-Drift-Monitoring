"""Target definition and label maturity (ADR-0004).

``target`` is 1 for charged-off/default, 0 for fully paid and missing while the loan
is still running. ``is_mature`` says whether the full term has elapsed by the data
snapshot, i.e. whether the observed outcome is free of survivorship bias.
"""

import numpy as np
import pandas as pd

BAD_STATUSES: frozenset[str] = frozenset(
    {"Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off"}
)
GOOD_STATUSES: frozenset[str] = frozenset(
    {"Fully Paid", "Does not meet the credit policy. Status:Fully Paid"}
)
OPEN_STATUSES: frozenset[str] = frozenset(
    {"Current", "In Grace Period", "Late (16-30 days)", "Late (31-120 days)"}
)


def map_target(status: pd.Series) -> pd.Series:
    """Map ``loan_status`` to 1 (bad), 0 (good) or NaN (still open).

    Raises:
        ValueError: if an unknown status appears (new statuses enter by decision).
    """
    known = BAD_STATUSES | GOOD_STATUSES | OPEN_STATUSES
    unknown = set(status.dropna().unique()) - known
    if unknown:
        raise ValueError(f"unknown loan_status values: {sorted(unknown)}")
    target = pd.Series(np.nan, index=status.index, dtype="float64")
    target[status.isin(BAD_STATUSES)] = 1.0
    target[status.isin(GOOD_STATUSES)] = 0.0
    return target


def maturity_date(issue_d: pd.Series, term_months: pd.Series) -> pd.Series:
    """First day of the month in which the last scheduled installment falls due."""
    month_index = issue_d.dt.year * 12 + (issue_d.dt.month - 1) + term_months.astype(int)
    return pd.to_datetime(
        {"year": month_index // 12, "month": month_index % 12 + 1, "day": 1}
    ).set_axis(issue_d.index)


def is_mature(issue_d: pd.Series, term_months: pd.Series, snapshot: pd.Timestamp) -> pd.Series:
    """True when the full term has elapsed by ``snapshot``."""
    return maturity_date(issue_d, term_months) <= snapshot
