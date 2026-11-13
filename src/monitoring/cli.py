"""``make calibrate`` (S0 bootstrap) and ``make detect`` (detector + Evidently over scenarios)."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import PROJECT_ROOT, get_settings
from src.data.features import model_feature_columns
from src.logging_config import configure_logging
from src.models.dataset import load_partition
from src.models.registry import load_alias, setup_tracking
from src.models.settings import load_training_config
from src.monitoring.calibration import bootstrap_null, calibrate_signal, composite_false_alarm
from src.monitoring.detect import Batch, DetectContext, detect_scenario
from src.monitoring.evaluation import evaluate
from src.monitoring.evidence import (
    alert_window,
    detection_record,
    evidently_section,
    pooled_current,
)
from src.monitoring.settings import THRESHOLDS_PATH, load_monitoring_config
from src.monitoring.severity import ALERTING
from src.reporting.run_record import RunRecord, git_state, next_run_id, write_record
from src.simulation.settings import scenario_ids

PROFILE_PATH = PROJECT_ROOT / "models" / "reference_profile.json"
EVIDENCE = PROJECT_ROOT / "docs" / "evidence" / "drift"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """CLI arguments."""
    parser = argparse.ArgumentParser(description="Drift calibration and detection.")
    parser.add_argument("command", choices=["calibrate", "detect"])
    parser.add_argument("--scenario", default="all", help="scenario id or 'all' (detect)")
    return parser.parse_args(argv)


def champion():
    """Registered champion model."""
    setup_tracking("training")
    return load_alias(load_training_config().registry_model_name)


def scores_of(model, frame: pd.DataFrame) -> np.ndarray:
    """Champion default probability for every row."""
    return np.asarray(model.predict_proba(frame[model_feature_columns()])[:, 1], dtype=float)


def thresholds_sha() -> str:
    """Short hash of the thresholds file used by a run."""
    return hashlib.sha256(THRESHOLDS_PATH.read_bytes()).hexdigest()[:12]


def write_json(path: Path, body: dict[str, Any]) -> None:
    """Strict JSON evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False, allow_nan=False), "utf-8")


def _calib_verdict(fa: dict[str, dict[str, float]]) -> str:
    p, c = fa["proposed"], fa["calibrated"]
    return (f"FA composto SEV-1+: proposto {p['sev1_plus']:.3f} → calibrado {c['sev1_plus']:.3f}; "
            f"SEV-2+: proposto {p['sev2_plus']:.3f} → calibrado {c['sev2_plus']:.3f}")  # fmt: skip


def run_calibrate(profile: dict[str, Any], git: tuple[str, bool]) -> None:
    """Bootstrap the control population and write the calibration evidence + RUN record."""
    cfg = load_monitoring_config()
    holdout = load_partition("holdout")
    null = bootstrap_null(holdout, scores_of(champion(), holdout), profile, cfg)
    cuts = {s: calibrate_signal(null, s, cfg) for s in [*ALERTING, "segment_gap"]}
    proposed = {s: {k: v for k, v in c["proposed"].items()} for s, c in cuts.items()}
    fa = {"proposed": composite_false_alarm(null, proposed, cfg),
          "calibrated": composite_false_alarm(null, cuts, cfg)}  # fmt: skip
    rec = RunRecord(
        run_id=next_run_id("calib", "S0"), kind="calib", scenario="S0", seed=cfg.calibration.seed,
        data_hash=thresholds_sha(), model=f"champion v{profile['model']['version']}",
        mlflow_ref="—", sha=git[0], dirty=git[1],
        metrics={s: {"q95": c["q95"], "q99": c["q99"], "max": c["max"],
                     "FA sev1 proposto": c["fa_proposed_sev1"], "sev1 calibrado": c["sev1"],
                     "sev2 calibrado": c.get("sev2")} for s, c in cuts.items()},
        verdict=_calib_verdict(fa),
        artifacts=["docs/evidence/drift/calibration_S0.json"],
        extra={"réplicas": cfg.calibration.replicates, "lote": cfg.calibration.batch_size},
    )  # fmt: skip
    run_id = write_record(rec).stem
    body = {"run_id": run_id, "replicates": len(null), "batch_size": cfg.calibration.batch_size,
            "signals": cuts, "false_alarm": fa}  # fmt: skip
    write_json(EVIDENCE / "calibration_S0.json", body)


def load_batches(sid: str) -> tuple[dict[str, Any], list[Batch]]:
    """Manifest and production view (applications, scored, labels) of a scenario."""
    folder = get_settings().data_dir / "simulated" / sid
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    batches = []
    for b in manifest["batches"]:
        f = folder / b["batch_id"]
        batches.append(Batch(b["index"], b["batch_id"], b["issue_month"], b["gate_status"],
                             *(pd.read_parquet(f / f"{n}.parquet")
                               for n in ("applications", "scored", "labels"))))  # fmt: skip
    return manifest, batches


def run_detect(sid: str, ctx: DetectContext, git: tuple[str, bool]) -> None:
    """Detect, evaluate against the manifest, build the Evidently report, write evidence."""
    manifest, batches = load_batches(sid)
    results = detect_scenario(ctx, batches)
    ev = evaluate(results, manifest["ground_truth"])
    current = pooled_current(batches, alert_window(results))
    sev1 = ctx.cfg.get("feature_psi").sev1
    report = evidently_section(ctx.reference, current, ctx.profile, sev1,
                               EVIDENCE / f"{sid}_evidently.html")  # fmt: skip
    meta = {"base_sha256": manifest["base_sha256"], "model": manifest["model"]["version"],
            "thresholds": thresholds_sha(), "sim_run": manifest.get("run_id")}  # fmt: skip
    body = {"scenario": sid, **meta, "evaluation": ev, "evidently": report, "batches": results}
    json.dumps(body, allow_nan=False)  # fail before any RUN record is written
    run_id = write_record(detection_record(sid, ev, meta, git)).stem
    write_json(EVIDENCE / f"{sid}.json", {"run_id": run_id, **body})


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    configure_logging(get_settings().log_level)
    args = parse_args(argv)
    git = git_state()
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if args.command == "calibrate":
        run_calibrate(profile, git)
        return 0
    reference = load_partition("reference")
    reference = reference[model_feature_columns()].assign(score=scores_of(champion(), reference))
    ctx = DetectContext(reference, profile, load_monitoring_config())
    for sid in scenario_ids() if args.scenario == "all" else [args.scenario]:
        run_detect(sid, ctx, git)
    return 0


if __name__ == "__main__":
    sys.exit(main())
