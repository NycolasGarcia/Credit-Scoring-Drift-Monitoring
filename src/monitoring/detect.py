"""Detection over one scenario: L2/L3/L4 per batch, severity and diagnosis (pure, no I/O).

The input is what production has: application batches, scored batches and labels that become
observable over time. The ground-truth manifest is never read here.
"""

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.monitoring.diagnosis import diagnose, unit_bugs
from src.monitoring.drift import drift_table
from src.monitoring.output import output_signals
from src.monitoring.performance import observable_at, performance_signals
from src.monitoring.settings import MonitoringConfig
from src.monitoring.severity import batch_severity

DETAIL_ROWS = 8


@dataclass(frozen=True)
class DetectContext:
    """Reference sample, profile and thresholds shared by every batch."""

    reference: pd.DataFrame
    profile: dict[str, Any]
    cfg: MonitoringConfig


@dataclass
class Batch:
    """One production batch as the monitoring job sees it."""

    index: int
    batch_id: str
    issue_month: str
    gate_status: str
    applications: pd.DataFrame
    scored: pd.DataFrame
    labels: pd.DataFrame


def history_frame(batches: list[Batch], features: list[str]) -> pd.DataFrame:
    """Scored rows of every batch with their (future) labels and the segment features."""
    parts = []
    for b in batches:
        part = b.scored[["loan_key", "score"]].merge(
            b.labels[["loan_key", "target", "label_batch"]], on="loan_key"
        )
        part = part.merge(b.applications[["loan_key", *features]], on="loan_key")
        parts.append(part.assign(cohort=b.index))
    return pd.concat(parts, ignore_index=True)


def _round(value: Any) -> Any:
    """JSON-safe number: 6 decimals, NaN as None."""
    if isinstance(value, float):
        return None if math.isnan(value) else round(value, 6)
    return value


def detect_batch(ctx: DetectContext, batch: Batch, history: pd.DataFrame) -> dict[str, Any]:
    """All signals, severity and diagnosis of one batch."""
    table = drift_table(ctx.reference, batch.applications, ctx.profile)
    l3 = output_signals(batch.scored, ctx.profile)
    k, min_rows = ctx.cfg.top_k_features, ctx.cfg.min_labeled_rows
    l4 = performance_signals(observable_at(history, batch.index), ctx.profile, k, min_rows)
    severity = batch_severity(table, l3, l4, ctx.cfg)
    bugs = unit_bugs(ctx.reference, batch.applications, table, ctx.profile, ctx.cfg)
    detail = table.head(DETAIL_ROWS).map(_round).to_dict(orient="records")
    return {
        "batch_id": batch.batch_id, "index": batch.index, "issue_month": batch.issue_month,
        "gate_status": batch.gate_status, "rows_scored": len(batch.scored),
        "l2_top": detail, "psi": dict(zip(table["feature"], table["psi"].round(6), strict=True)),
        "ks_p": {f: _round(p) for f, p in zip(table["feature"], table["ks_p"], strict=True)
                 if p is not None and not math.isnan(p)},
        "l3": {k: _round(v) for k, v in l3.items()},
        "l4": None if l4 is None else {k: _round(v) for k, v in l4.items()},
        "severity": severity, "unit_bugs": bugs,
        "diagnosis": diagnose(batch.gate_status, severity, l4, bugs, ctx.cfg),
    }  # fmt: skip


def detect_scenario(ctx: DetectContext, batches: list[Batch]) -> list[dict[str, Any]]:
    """Run the detector over a scenario's batches, in time order."""
    top = [f for f in ctx.profile["importance_rank"][: ctx.cfg.top_k_features]
           if ctx.profile["features"][f]["type"] == "numeric"]  # fmt: skip
    history = history_frame(batches, top)
    return [detect_batch(ctx, b, history) for b in batches]
