"""Batch state -> metric samples (names and labels from the catalog in ``metrics.py``)."""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.observability.events import StepLog
from src.observability.metrics import Sample

STATUS = {"ok": 1.0, "failed": 0.0, "skipped": -1.0}


@dataclass
class BatchState:
    """Everything the job learned about one batch."""

    index: int
    batch_id: str
    issue_month: str
    log: StepLog
    report: dict[str, Any] = field(default_factory=dict)
    scored: pd.DataFrame = field(default_factory=pd.DataFrame)
    table: pd.DataFrame | None = None
    l3: dict[str, Any] = field(default_factory=dict)
    l4: dict[str, Any] | None = None
    severity: dict[str, Any] = field(default_factory=lambda: {"signals": {}, "level": 0})
    diagnosis: str = "none"
    unit_bugs: dict[str, Any] = field(default_factory=dict)
    levels: dict[str, int] = field(default_factory=dict)
    finished_at: float = 0.0


def _operational(s: BatchState) -> list[Sample]:
    info = {"batch_id": s.batch_id, "issue_month": s.issue_month}
    out: list[Sample] = [("cdm_batch_index", {}, float(s.index)), ("cdm_batch_info", info, 1.0)]
    for e in s.log.events:
        out.append(("cdm_step_status", {"step": e["step"]}, STATUS[e["status"]]))
        out.append(("cdm_step_duration_seconds", {"step": e["step"]}, e["duration_ms"] / 1000))
    out.append(("cdm_batch_duration_seconds", {}, sum(s.log.durations_s().values())))
    r = s.report
    for stage, key in (
        ("in", "rows_in"),
        ("valid", "rows_valid"),
        ("quarantined", "rows_quarantined"),
    ):
        out.append(("cdm_batch_rows", {"stage": stage}, float(r.get(key, 0))))
    out.append(("cdm_batch_rows", {"stage": "scored"}, float(len(s.scored))))
    out.append(("cdm_gate_blocked", {}, float(r.get("status") == "blocked")))
    if not s.log.failed():
        out.append(("cdm_last_success_timestamp_seconds", {}, s.finished_at))
    return out


def _model(s: BatchState, feature_sev1: float) -> list[Sample]:
    out: list[Sample] = []
    if s.table is not None:
        out += [("cdm_feature_psi", {"feature": f}, float(v))
                for f, v in zip(s.table["feature"], s.table["psi"], strict=True)]  # fmt: skip
        out.append(("cdm_features_drifted", {}, float((s.table["psi"] >= feature_sev1).sum())))
    l3 = {"cdm_score_psi": "score_psi", "cdm_approval_rate": "approval_rate",
          "cdm_expected_bad_rate": "expected_bad_rate"}  # fmt: skip
    out += [(m, {}, float(s.l3[k])) for m, k in l3.items() if s.l3.get(k) is not None]
    if s.l4:
        l4 = {"cdm_observed_bad_rate": "bad_rate_observed", "cdm_bad_rate_ratio": "bad_rate_ratio",
              "cdm_auc_mature": "auc", "cdm_labeled_rows": "n_labeled"}  # fmt: skip
        out += [(m, {}, float(s.l4[k])) for m, k in l4.items()]
    return out


def _alerts(s: BatchState) -> list[Sample]:
    out: list[Sample] = [("cdm_signal_severity", {"signal": k}, float(v))
                         for k, v in s.severity["signals"].items()]  # fmt: skip
    out.append(("cdm_batch_severity", {}, float(s.severity["level"])))
    out += [("cdm_alert_level", {"alert": k}, float(v)) for k, v in s.levels.items()]
    for sev in (1, 2, 3):
        count = sum(v == sev for v in s.levels.values())
        out.append(("cdm_alerts_firing", {"severity": f"SEV-{sev}"}, float(count)))
    out.append(("cdm_diagnosis", {"code": s.diagnosis}, 1.0))
    return out


def batch_samples(state: BatchState, feature_sev1: float) -> list[Sample]:
    """All gauges of one batch."""
    return [*_operational(state), *_model(state, feature_sev1), *_alerts(state)]
