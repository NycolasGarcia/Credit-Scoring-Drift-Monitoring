"""RUN record of a scenario generation (kind ``sim``): one per scenario, from its manifest."""

from collections import defaultdict
from typing import Any

from src.reporting.run_record import RunRecord, next_run_id
from src.simulation.settings import ScenarioConfig

METRICS = ("approval_rate", "mean_score", "bad_rate_true", "labeled_share")


def phase_of(cfg: ScenarioConfig, batch: dict[str, Any]) -> str:
    """Grouping used in the record: before/after the drift, or calendar year for S0/S5."""
    if cfg.schedule.shape == "none":
        return batch["issue_month"][:4]
    return "pré-drift" if batch["intensity"] == 0 else "pós-onset"


def phase_metrics(cfg: ScenarioConfig, batches: list[dict[str, Any]]) -> dict[str, dict]:
    """Row-weighted means of the batch aggregates, per phase."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in batches:
        groups[phase_of(cfg, b)].append(b)
    return {phase: _weighted(rows) for phase, rows in groups.items()}


def _weighted(rows: list[dict[str, Any]]) -> dict[str, float]:
    out = {"lotes": float(len(rows)), "linhas": float(sum(r["rows"] for r in rows))}
    for m in METRICS:
        pairs = [(r[m], r["rows"]) for r in rows if r[m] is not None]
        if pairs:
            out[m] = sum(v * w for v, w in pairs) / sum(w for _, w in pairs)
    return out


def _verdict(cfg: ScenarioConfig, batches: list[dict[str, Any]]) -> str:
    blocked = sum(b["gate_status"] == "blocked" for b in batches)
    scored = sum(b["rows_scored"] for b in batches)
    return (f"{len(batches)} lotes · {blocked} bloqueados · {scored} linhas pontuadas · "
            f"diagnóstico esperado {cfg.expected.diagnosis}")  # fmt: skip


def build_record(cfg: ScenarioConfig, manifest: dict[str, Any], git: tuple[str, bool]) -> RunRecord:
    """RUN record for one generated scenario."""
    batches = manifest["batches"]
    return RunRecord(
        run_id=next_run_id("sim", cfg.id), kind="sim", scenario=cfg.id, seed=cfg.seed,
        data_hash=manifest["base_sha256"], model=manifest["model"]["version"],
        mlflow_ref="—", metrics=phase_metrics(cfg, batches), verdict=_verdict(cfg, batches),
        artifacts=[f"data/simulated/{cfg.id}/", f"docs/evidence/scenarios/{cfg.id}.json"],
        extra={"config_sha256": manifest["config_sha256"], "drift": cfg.drift_type,
               "onset": manifest["ground_truth"]["onset_batch"], "label_lag": cfg.label_lag,
               "quarentena (linhas)": sum(b["rows_quarantined"] for b in batches)},
        sha=git[0], dirty=git[1],
    )  # fmt: skip
