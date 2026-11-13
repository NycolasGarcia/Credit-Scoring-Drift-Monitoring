"""Evidently report with an explicit, registered test per column (API verified on 0.7.23, NV-8).

Evidently's built-in PSI bins numeric columns with equal-width (Sturges) edges computed on
reference + current together, so the current batch shapes its own bins and heavy tails
collapse into one bin. The report therefore registers ``psi_ref``: PSI with reference-quantile
bins, the same rule as the reference profile. Evidently drops nulls before calling a test,
so null-rate drift is visible only in the project's own PSI (null bin) and contract rule S01.
"""

from pathlib import Path
from typing import Any

import pandas as pd
from evidently import DataDefinition, Dataset, Report
from evidently.legacy.calculations.stattests.registry import StatTest, register_stattest
from evidently.legacy.core import ColumnType
from evidently.presets import DataDriftPreset

from src.monitoring.profile import N_BINS
from src.monitoring.psi import (
    categorical_proportions,
    numeric_proportions,
    psi_from_proportions,
    quantile_edges,
)

METHOD = "psi_ref"


def _psi_ref(reference_data: pd.Series, current_data: pd.Series, feature_type, threshold: float):
    if feature_type == ColumnType.Categorical:
        levels = sorted(reference_data.astype(str).unique().tolist())
        ref = categorical_proportions(reference_data.astype(str), levels)
        cur = categorical_proportions(current_data.astype(str), levels)
    else:
        edges = quantile_edges(reference_data, N_BINS)
        ref, cur = (
            numeric_proportions(reference_data, edges),
            numeric_proportions(current_data, edges),
        )
    value = psi_from_proportions(ref, cur)
    return value, value >= threshold


def register_psi_ref() -> None:
    """Register ``psi_ref`` in Evidently's stat-test registry (re-registering overwrites)."""
    test = StatTest(
        name=METHOD,
        display_name="PSI (bins da referência)",
        default_threshold=0.1,
        allowed_feature_types=[ColumnType.Numerical, ColumnType.Categorical],
    )
    register_stattest(test, _psi_ref)


def build_report(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    numeric: list[str],
    categorical: list[str],
    threshold: float,
):
    """Run the drift report; every column uses ``psi_ref`` with the given threshold."""
    register_psi_ref()
    cols = [*numeric, *categorical]
    dd = DataDefinition(numerical_columns=numeric, categorical_columns=categorical)
    preset = DataDriftPreset(columns=cols, method=METHOD, threshold=threshold)
    current_ds = Dataset.from_pandas(current[cols], data_definition=dd)
    return Report([preset]).run(
        current_ds, Dataset.from_pandas(reference[cols], data_definition=dd)
    )


def column_values(snapshot) -> dict[str, float]:
    """Drift value per column, read back from the snapshot."""
    return {m["config"]["column"]: float(m["value"]) for m in snapshot.dict()["metrics"]
            if m["config"].get("type", "").endswith("ValueDrift")}  # fmt: skip


def save_html(snapshot, path: Path) -> Path:
    """Write the interactive HTML report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot.save_html(str(path))
    return path


def drifted_columns(values: dict[str, Any], threshold: float) -> list[str]:
    """Columns flagged by the report, most drifted first."""
    return sorted((c for c, v in values.items() if v >= threshold), key=lambda c: -values[c])
