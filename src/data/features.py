"""Origination-time feature allowlist and derived features.

A column enters the model only if the inventory marks it ``use: feature`` and
``cat: originacao``. New columns in the source never enter by omission.
"""

import pandas as pd

from src.data.inventory import load_inventory

CATEGORICAL_FEATURES: tuple[str, ...] = (
    "grade",
    "home_ownership",
    "verification_status",
    "purpose",
)
DERIVED_FEATURES: tuple[str, ...] = ("credit_history_months",)
SEGMENT_COLUMNS: tuple[str, ...] = ("addr_state", "emp_length", "home_ownership")


def raw_feature_columns() -> list[str]:
    """Raw columns allowed into the model, straight from the inventory."""
    inv = load_inventory()
    return [c for c in inv.by_use("feature") if inv.columns[c].cat == "originacao"]


def model_feature_columns() -> list[str]:
    """Raw allowlist plus derived features: the exact model input schema."""
    return [*raw_feature_columns(), *DERIVED_FEATURES]


def numeric_features() -> list[str]:
    """Model features treated as numeric."""
    return [c for c in model_feature_columns() if c not in CATEGORICAL_FEATURES]


def credit_history_months(issue_d: pd.Series, earliest_cr_line: pd.Series) -> pd.Series:
    """Months between the first credit line and the loan issue date."""
    months = (issue_d.dt.year - earliest_cr_line.dt.year) * 12 + (
        issue_d.dt.month - earliest_cr_line.dt.month
    )
    return months.astype("float64")


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with derived features added and their raw inputs removed."""
    out = df.copy()
    out["credit_history_months"] = credit_history_months(out["issue_d"], out["earliest_cr_line"])
    return out.drop(columns=["earliest_cr_line"])
