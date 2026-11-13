"""Quality gate (GR-1, GR-2): validate -> (ok) score -> validate output | (fail) quarantine.

A blocked batch produces zero scored rows, a quarantine folder with an aggregate report,
an ERROR log event with the alert id and a non-zero exit code.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.contracts.report import build_report, write_quarantine
from src.contracts.schema import KEY
from src.contracts.settings import ContractConfig
from src.contracts.validate import validate_input, validate_output
from src.data.features import model_feature_columns

logger = logging.getLogger(__name__)
EXIT_OK, EXIT_BLOCKED = 0, 2
ALERT_BLOCKED = "CONTRACT_BATCH_BLOCKED"


@dataclass
class GateOutcome:
    """What the gate did with one batch."""

    status: str
    scored: pd.DataFrame
    report: dict[str, Any]
    quarantine_dir: Path | None

    @property
    def exit_code(self) -> int:
        """Process exit code for the batch job."""
        return EXIT_BLOCKED if self.status in {"blocked", "output_failed"} else EXIT_OK


def score_batch(model, valid: pd.DataFrame, threshold: float, version: str) -> pd.DataFrame:
    """Score valid rows and decide approve/reject (approve when score < threshold)."""
    p = np.asarray(model.predict_proba(valid[model_feature_columns()])[:, 1], dtype=float)
    return pd.DataFrame({
        KEY: valid[KEY].to_numpy(), "score": p,
        "decision": np.where(p < threshold, "approve", "reject"), "model_version": version,
    })  # fmt: skip


def _log(report: dict[str, Any], level: int) -> None:
    extra = {
        k: report[k] for k in ("batch_id", "status", "rows_in", "rows_valid", "rows_quarantined")
    }
    extra["rules"] = {v["rule"]: v["count"] for v in report["hard_violations"]}
    if level >= logging.ERROR:
        extra["alert"] = ALERT_BLOCKED
    logger.log(level, "contract gate", extra=extra)


@dataclass(frozen=True)
class GateContext:
    """Everything the gate needs besides the batch itself."""

    model: Any
    threshold: float
    version: str
    profile: dict[str, Any]
    cfg: ContractConfig
    quarantine_root: Path


def run_gate(batch: pd.DataFrame, batch_id: str, ctx: GateContext) -> GateOutcome:
    """Validate, quarantine and (if allowed) score one application batch."""
    result = validate_input(batch, ctx.profile, ctx.cfg)
    report = build_report(result, batch_id, ctx.cfg)
    folder = write_quarantine(result, report, ctx.quarantine_root)
    if result.status == "blocked":
        _log(report, logging.ERROR)
        return GateOutcome("blocked", pd.DataFrame(), report, folder)
    scored = score_batch(ctx.model, result.valid, ctx.threshold, ctx.version)
    output_fails = validate_output(scored, ctx.cfg, ctx.threshold)
    report["output_violations"] = output_fails
    if output_fails:
        report["status"] = "output_failed"
        _log(report, logging.ERROR)
        return GateOutcome("output_failed", pd.DataFrame(), report, folder)
    _log(report, logging.WARNING if result.status == "partial" else logging.INFO)
    return GateOutcome(result.status, scored, report, folder)
