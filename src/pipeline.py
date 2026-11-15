"""Monitoring job per batch.

Steps: ingest → validate → score → detect → evaluate → alert → respond → record.

Each step emits a structured event (``src/observability/events.py``). A failed step does not
hide the batch: the remaining core steps are skipped, but alert and record still run, so the
failure becomes a metric, an alert (CDM_STEP_FAILED) and a log line. ``respond`` is the policy
engine of F7 and is recorded as skipped until then.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from src.alerting.engine import BatchFacts, alert_levels
from src.alerting.settings import AlertConfig
from src.contracts.gate import score_batch
from src.contracts.report import build_report, write_quarantine
from src.contracts.settings import ContractConfig
from src.contracts.validate import validate_input, validate_output
from src.monitoring.detect import Batch, history_frame
from src.monitoring.diagnosis import diagnose, unit_bugs
from src.monitoring.drift import drift_table
from src.monitoring.output import output_signals
from src.monitoring.performance import observable_at, performance_signals
from src.monitoring.settings import MonitoringConfig
from src.monitoring.severity import batch_severity
from src.observability.events import StepLog
from src.observability.samples import BatchState

logger = logging.getLogger("cdm.pipeline")
CORE = ("ingest", "validate", "score", "detect", "evaluate")
AFTER_BLOCK = {"score", "detect", "evaluate"}


@dataclass(frozen=True)
class JobContext:
    """Everything shared by the batches of one run."""

    run_id: str
    model: Any
    version: str
    profile: dict[str, Any]
    reference: pd.DataFrame
    contract: ContractConfig
    monitoring: MonitoringConfig
    alerts: AlertConfig
    quarantine_root: Path


@dataclass
class RunMemory:
    """State carried across batches: label history, durations, blocked streak."""

    history: pd.DataFrame = field(default_factory=pd.DataFrame)
    durations: list[float] = field(default_factory=list)
    blocked_streak: int = 0

    def segment_features(self, ctx: JobContext) -> list[str]:
        """Top-k numeric features kept in the history (L4 segment gap)."""
        top = ctx.profile["importance_rank"][: ctx.monitoring.top_k_features]
        return [f for f in top if ctx.profile["features"][f]["type"] == "numeric"]


@dataclass(frozen=True)
class BatchInput:
    """Where one batch lives and what production knows about it."""

    index: int
    batch_id: str
    issue_month: str
    folder: Path


def _ingest(ctx, item, state, data, mem, rows) -> None:
    data["apps"] = pd.read_parquet(item.folder / "applications.parquet")
    data["labels"] = pd.read_parquet(item.folder / "labels.parquet")
    rows["rows_in"] = rows["rows_out"] = len(data["apps"])


def _validate(ctx, item, state, data, mem, rows) -> None:
    result = validate_input(data["apps"], ctx.profile, ctx.contract)
    state.report = build_report(result, item.batch_id, ctx.contract)
    write_quarantine(result, state.report, ctx.quarantine_root)
    data["result"] = result
    rows.update(rows_in=result.rows_in, rows_out=len(result.valid),
                rows_quarantined=len(result.quarantined))  # fmt: skip


def _score(ctx, item, state, data, mem, rows) -> None:
    valid = data["result"].valid
    scored = score_batch(ctx.model, valid, ctx.profile["threshold"], ctx.version)
    if fails := validate_output(scored, ctx.contract, ctx.profile["threshold"]):
        raise RuntimeError(f"output contract failed: {sorted(fails)}")
    state.scored = scored
    batch = Batch(item.index, item.batch_id, item.issue_month, "passed", data["apps"], scored,
                  data["labels"])  # fmt: skip
    mem.history = pd.concat([mem.history, history_frame([batch], mem.segment_features(ctx))])
    rows.update(rows_in=len(valid), rows_out=len(scored))


def _detect(ctx, item, state, data, mem, rows) -> None:
    state.table = drift_table(ctx.reference, data["apps"], ctx.profile)
    state.l3 = output_signals(state.scored, ctx.profile)
    state.unit_bugs = unit_bugs(ctx.reference, data["apps"], state.table, ctx.profile,
                                ctx.monitoring)  # fmt: skip


def _evaluate(ctx, item, state, data, mem, rows) -> None:
    cfg = ctx.monitoring
    matured = observable_at(mem.history, item.index)
    state.l4 = performance_signals(matured, ctx.profile, cfg.top_k_features, cfg.min_labeled_rows)
    state.severity = batch_severity(state.table, state.l3, state.l4, cfg)
    state.diagnosis = diagnose("passed", state.severity, state.l4, state.unit_bugs, cfg)
    rows["rows_in"] = len(matured)


STEPS = {"ingest": _ingest, "validate": _validate, "score": _score, "detect": _detect,
         "evaluate": _evaluate}  # fmt: skip


def _skip(name: str, state: BatchState, data: dict[str, Any]) -> bool:
    blocked = state.report.get("status") == "blocked"
    return data.get("failed", False) or (blocked and name in AFTER_BLOCK)


def _core(ctx: JobContext, item: BatchInput, state: BatchState, mem: RunMemory) -> None:
    data: dict[str, Any] = {}
    for name in CORE:
        if _skip(name, state, data):
            state.log.skip(name)
            continue
        try:
            with state.log.step(name) as rows:
                STEPS[name](ctx, item, state, data, mem, rows)
        except Exception:
            logger.exception("step failed", extra={"batch_id": item.batch_id, "step": name})
            data["failed"] = True
    if state.report.get("status") == "blocked":
        state.diagnosis = "D0"


def _alert(ctx: JobContext, state: BatchState, mem: RunMemory) -> None:
    blocked = state.report.get("status") == "blocked"
    mem.blocked_streak = mem.blocked_streak + 1 if blocked else 0
    durations = sorted(mem.durations)
    facts = BatchFacts(
        signals=state.severity["signals"], gate_status="blocked" if blocked else "passed",
        blocked_streak=mem.blocked_streak,
        soft_triggered=len(state.report.get("soft_warnings", {})),
        unit_bugs=state.unit_bugs, failed_steps=state.log.failed(),
        duration_s=sum(state.log.durations_s().values()),
        median_duration_s=durations[len(durations) // 2] if durations else None,
    )  # fmt: skip
    with state.log.step("alert"):
        state.levels = alert_levels(facts, ctx.alerts)
    mem.durations.append(facts.duration_s)


def run_batch(ctx: JobContext, item: BatchInput, mem: RunMemory) -> BatchState:
    """Run every step of one batch; failures are recorded, never swallowed silently."""
    state = BatchState(
        item.index, item.batch_id, item.issue_month, StepLog(ctx.run_id, item.batch_id)
    )
    _core(ctx, item, state, mem)
    _alert(ctx, state, mem)
    state.log.skip("respond")  # policy engine: F7
    state.finished_at = time.time()
    return state
