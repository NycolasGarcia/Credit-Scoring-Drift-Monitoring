"""Pandera schemas built from the contract config and the reference profile.

Check names carry the rule id (``H05``...) so every failure maps back to the catalog.
"""

from typing import Any

import numpy as np
import pandas as pd
import pandera.pandas as pa

from src.contracts.settings import ContractConfig
from src.data.features import CATEGORICAL_FEATURES, model_feature_columns

KEY, DATE = "loan_key", "issue_d"
SEGMENTS = ("addr_state",)
DECILE_EDGES = 9


def application_columns() -> list[str]:
    """Exact column set of an application batch (the input contract)."""
    return [KEY, DATE, *model_feature_columns(), *SEGMENTS]


def to_application_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Project a processed partition onto the application schema (labels removed)."""
    return df[application_columns()].reset_index(drop=True)


def reference_median(profile: dict[str, Any], feature: str) -> float:
    """Median of a numeric feature from the reference profile's decile edges."""
    edges = profile["features"][feature]["edges"]
    if len(edges) != DECILE_EDGES:
        raise ValueError(f"{feature}: expected {DECILE_EDGES} decile edges, got {len(edges)}")
    return float(edges[4])


def _numeric_checks(col: str, cfg: ContractConfig) -> list[pa.Check]:
    rules, checks = cfg.input, []
    if col in rules.ranges:
        lo, hi = rules.ranges[col]
        checks.append(pa.Check(lambda s, lo=lo, hi=hi: s.between(lo, hi), name="H05"))
    if col in rules.non_negative:
        checks.append(pa.Check(lambda s: s >= 0, name="H11"))
    if col in rules.domains:
        checks.append(pa.Check(lambda s, d=rules.domains[col]: s.isin(d), name="H06"))
    if col in rules.sentinels:
        checks.append(pa.Check(lambda s, v=rules.sentinels[col]: ~s.isin(v), name="H09"))
    return checks


def _column(col: str, cfg: ContractConfig) -> pa.Column:
    nullable = col not in cfg.input.required
    if col == KEY:
        return pa.Column(str, nullable=False)
    if col == DATE:
        win = cfg.batch.issue_date_window
        in_window = pa.Check(
            lambda s: s.between(pd.Timestamp(win.min), pd.Timestamp(win.max)), name="H07"
        )
        return pa.Column("datetime64[ns]", in_window, nullable=False)
    if col in CATEGORICAL_FEATURES or col in SEGMENTS:
        domain = cfg.input.domains.get(col)
        checks = [pa.Check(lambda s, d=domain: s.isin(d), name="H06")] if domain else []
        return pa.Column(str, checks, nullable=nullable)
    dtype = "int64" if col in cfg.input.integer_columns else float
    return pa.Column(dtype, _numeric_checks(col, cfg), nullable=nullable)


def amortized_installment(df: pd.DataFrame) -> pd.Series:
    """Monthly installment by the French amortization formula (loan_amnt, int_rate %, term)."""
    r = df["int_rate"] / 100 / 12
    return df["loan_amnt"] * r / (1 - (1 + r) ** (-df["term"]))


def amortization_error(df: pd.DataFrame) -> pd.Series:
    """Relative gap between the stated installment and the French amortization formula."""
    return (df["installment"] / amortized_installment(df) - 1).abs()


def _frame_checks(cfg: ContractConfig, income_median: float) -> list[pa.Check]:
    tol, band = cfg.input.installment_tolerance, cfg.batch.income_scale

    def income_scale(df: pd.DataFrame) -> bool:
        ratio = df["annual_inc"].median() / income_median
        return bool(band.min_ratio <= ratio <= band.max_ratio)

    def coherent(df: pd.DataFrame) -> pd.Series:
        return (amortization_error(df) <= tol) | df["installment"].isna()

    return [pa.Check(coherent, name="H08"), pa.Check(income_scale, name="H10")]


def input_schema(cfg: ContractConfig, profile: dict[str, Any]) -> pa.DataFrameSchema:
    """Input (application batch) contract."""
    columns = {c: _column(c, cfg) for c in application_columns()}
    checks = _frame_checks(cfg, reference_median(profile, "annual_inc"))
    return pa.DataFrameSchema(columns, checks=checks, strict=True, unique=[KEY], coerce=False)


def output_schema(cfg: ContractConfig, threshold: float) -> pa.DataFrameSchema:
    """Output (scored batch) contract."""

    def consistent(df: pd.DataFrame) -> bool:
        return bool(np.array_equal(df["score"] < threshold, df["decision"] == "approve"))

    in_unit = pa.Check(lambda s: s.between(0, 1), name="O02")
    in_domain = pa.Check(lambda s: s.isin(cfg.output.decisions), name="O02")
    columns = {
        KEY: pa.Column(str, nullable=False),
        "score": pa.Column(float, in_unit, nullable=False),
        "decision": pa.Column(str, in_domain, nullable=False),
        "model_version": pa.Column(str, nullable=False),
    }
    checks = [pa.Check(consistent, name="O03")]
    return pa.DataFrameSchema(columns, checks=checks, strict=True, unique=[KEY], coerce=False)
