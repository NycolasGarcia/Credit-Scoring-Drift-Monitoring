"""Ground-truth manifest per scenario: what changed, where, when, how much (aggregates only)."""

import hashlib
import json
import math
from typing import Any

import pandas as pd

from src.contracts.gate import GateOutcome
from src.data.split import content_hash
from src.simulation.engine import TARGET, SimBatch
from src.simulation.settings import ScenarioConfig
from src.simulation.transforms import drifted_features

TRACKED = ("annual_inc", "dti", "int_rate", "installment")


def _num(value: Any) -> float | None:
    value = float(value)
    return None if math.isnan(value) else round(value, 6)


def config_hash(cfg: ScenarioConfig) -> str:
    """SHA-256 of the validated scenario config."""
    return hashlib.sha256(cfg.model_dump_json().encode("utf-8")).hexdigest()


def _scored_stats(scored: pd.DataFrame) -> dict[str, Any]:
    if scored.empty:
        return {"rows_scored": 0, "approval_rate": None, "mean_score": None}
    return {"rows_scored": len(scored), "mean_score": _num(scored["score"].mean()),
            "approval_rate": _num((scored["decision"] == "approve").mean())}  # fmt: skip


def batch_summary(batch: SimBatch, outcome: GateOutcome) -> dict[str, Any]:
    """Aggregates of one batch: volume, gate, decision, labels, tracked feature means."""
    labels, apps = batch.labels, batch.applications
    return {
        "batch_id": batch.batch_id, "index": batch.index, "issue_month": batch.issue_month,
        "intensity": batch.level, "rows": len(apps), "bug_rows": batch.bug_rows,
        "gate_status": outcome.status, "rows_quarantined": outcome.report["rows_quarantined"],
        **_scored_stats(outcome.scored),
        "labeled_share": _num(labels[TARGET].notna().mean()),
        "bad_rate_true": _num(labels[TARGET].mean()),
        "mean_p_oracle": _num(labels["p_oracle"].mean()),
        "feature_means": {f: _num(apps[f].mean()) for f in TRACKED},
        "hashes": {"applications": content_hash(apps), "labels": content_hash(labels)},
    }  # fmt: skip


def ground_truth(cfg: ScenarioConfig) -> dict[str, Any]:
    """What the detector should find, stated by design."""
    return {
        "drift_type": cfg.drift_type,
        "drifted_features": drifted_features(cfg.transforms),
        "label_mechanism": [t.model_dump() for t in cfg.transforms if t.kind == "logit_shift"],
        "onset_batch": cfg.schedule.onset if cfg.schedule.shape != "none" else None,
        "expected_layers": cfg.expected.layers,
        "expected_diagnosis": cfg.expected.diagnosis,
    }


def build_manifest(
    cfg: ScenarioConfig, base_hash: str, model: dict[str, Any], batches: list[dict[str, Any]]
) -> dict[str, Any]:
    """Full manifest for one scenario."""
    return {"scenario": cfg.id, "name": cfg.name, "config": cfg.model_dump(mode="json"),
            "config_sha256": config_hash(cfg), "base_sha256": base_hash, "model": model,
            "ground_truth": ground_truth(cfg), "batches": batches}  # fmt: skip


def dumps(manifest: dict[str, Any]) -> str:
    """Strict JSON (no NaN)."""
    return json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False)
