"""Contract validation: hard rules decide block / quarantine; soft rules only warn.

Pandera runs with ``lazy=True`` so every failure is collected. Failure *values* are never
kept: the result carries rule ids, counts and row positions only (GR-10).
"""

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd
import pandera.pandas as pa

from src.contracts.rules import classify
from src.contracts.schema import input_schema, output_schema
from src.contracts.settings import ContractConfig
from src.data.features import CATEGORICAL_FEATURES

Status = Literal["passed", "partial", "blocked"]


@dataclass
class ContractResult:
    """Outcome of validating one batch."""

    status: Status
    rows_in: int
    rows_failed: int
    valid: pd.DataFrame
    quarantined: pd.DataFrame
    rule_counts: dict[str, int]
    soft: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def row_failure_rate(self) -> float:
        """Share of rows failing row-scope rules (independent of whether the batch was blocked)."""
        return self.rows_failed / self.rows_in if self.rows_in else 0.0


def failures(schema: pa.DataFrameSchema, batch: pd.DataFrame) -> pd.DataFrame:
    """All failure cases classified by rule (empty frame when the batch is valid)."""
    try:
        schema.validate(batch, lazy=True)
    except pa.errors.SchemaErrors as err:
        return classify(err.failure_cases)
    return pd.DataFrame(columns=["column", "check", "index", "rule", "scope"])


def rule_counts(fails: pd.DataFrame) -> dict[str, int]:
    """Failures per rule: distinct rows for row-level failures, occurrences otherwise.

    A DataFrame-level check that returns a boolean Series is reported by pandera once per
    column of each failing row, so rows must be de-duplicated.
    """
    counts = {}
    for rule, group in fails.groupby("rule"):
        rows = group["index"].dropna()
        counts[str(rule)] = int(rows.nunique()) if len(rows) else len(group)
    return counts


def decide(
    fails: pd.DataFrame, batch: pd.DataFrame, cfg: ContractConfig
) -> tuple[Status, pd.Index]:
    """Block on schema/batch rules or too many bad rows; otherwise quarantine bad rows."""
    row_idx = pd.Index(fails.loc[fails["scope"] == "row", "index"].dropna().astype(int).unique())
    blocking = fails["scope"].isin(["schema", "batch"]).any()
    too_many = len(row_idx) / max(len(batch), 1) > cfg.batch.max_row_failure_rate
    if blocking or too_many:
        return "blocked", row_idx
    return ("partial" if len(row_idx) else "passed"), row_idx


def soft_checks(batch: pd.DataFrame, profile: dict[str, Any], cfg: ContractConfig) -> dict:
    """Warning-only rules S01-S04 with aggregated evidence."""
    soft, feats = cfg.soft, profile["features"]
    null_jump = {c: round(float(batch[c].isna().mean() - f["ref_props"]["__null__"]), 4)
                 for c, f in feats.items() if c in batch}  # fmt: skip
    null_jump = {c: v for c, v in null_jump.items() if v > soft.null_rate_tolerance}
    new_levels = {c: sorted(set(batch[c].dropna().astype(str)) - set(feats[c]["levels"]))
                  for c in CATEGORICAL_FEATURES if c in batch}  # fmt: skip
    new_levels = {c: v for c, v in new_levels.items() if v}
    util = [c for c in ("revol_util", "bc_util") if c in batch]
    tail = float((batch[util] > soft.utilization_ceiling).any(axis=1).mean()) if util else 0.0
    return {
        "S01": {"triggered": bool(null_jump), "columns": null_jump},
        "S02": {"triggered": bool(new_levels), "new_levels": new_levels},
        "S03": {
            "triggered": not soft.volume.min <= len(batch) <= soft.volume.max,
            "rows": len(batch),
        },
        "S04": {"triggered": tail > soft.extreme_tail_max_share, "share": round(tail, 5)},
    }


def validate_input(
    batch: pd.DataFrame, profile: dict[str, Any], cfg: ContractConfig
) -> ContractResult:
    """Validate an application batch against the input contract."""
    batch = batch.reset_index(drop=True)
    fails = failures(input_schema(cfg, profile), batch)
    status, bad = decide(fails, batch, cfg)
    counts = rule_counts(fails)
    valid = batch.iloc[0:0] if status == "blocked" else batch.drop(index=bad)
    quarantined = batch if status == "blocked" else batch.loc[bad]
    soft = soft_checks(batch, profile, cfg) if "H01" not in counts else {}
    return ContractResult(status, len(batch), len(bad), valid, quarantined, counts, soft)


def validate_output(scored: pd.DataFrame, cfg: ContractConfig, threshold: float) -> dict[str, int]:
    """Validate a scored batch; returns rule counts (empty when valid)."""
    fails = failures(output_schema(cfg, threshold), scored)
    if not len(fails):
        return {}
    rules = fails["rule"].where(fails["rule"].isin(["O02", "O03"]), "O01")
    return rules.value_counts().astype(int).to_dict()
