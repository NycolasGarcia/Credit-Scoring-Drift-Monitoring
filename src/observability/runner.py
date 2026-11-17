"""``make monitor`` / ``make replay``: run the monitoring job over a scenario's batches.

Per batch: the pipeline steps, then ``record`` (Pushgateway + MLflow child run). Per run: a
JSON-lines log, a summary, an MLflow parent run with artifacts and a RUN record.
"""

import argparse
import json
import sys
import time
from collections import Counter
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import mlflow

from src.alerting.engine import active
from src.alerting.settings import load_alert_config
from src.config import PROJECT_ROOT, get_settings
from src.contracts.settings import load_contract_config
from src.data.features import model_feature_columns
from src.logging_config import configure_logging
from src.models.dataset import load_partition
from src.models.registry import load_alias, setup_tracking
from src.models.settings import load_training_config
from src.monitoring.settings import load_monitoring_config
from src.observability.events import attach_run_log, detach_run_log
from src.observability.metrics import as_dict, push
from src.observability.samples import BatchState, batch_samples
from src.pipeline import BatchInput, JobContext, RunMemory, run_batch
from src.reporting.run_record import RunRecord, git_state, next_run_id, write_record

PROFILE_PATH = PROJECT_ROOT / "models" / "reference_profile.json"
EVIDENTLY = PROJECT_ROOT / "docs" / "evidence" / "drift"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """CLI arguments."""
    p = argparse.ArgumentParser(description="Run the monitoring job over a scenario.")
    p.add_argument("--scenario", default="S1")
    p.add_argument("--interval", type=float, default=0.0, help="seconds between batches (replay)")
    p.add_argument("--limit", type=int, default=0, help="process only the first N batches")
    p.add_argument("--push", action="store_true", help="publish metrics to the Pushgateway")
    p.add_argument("--no-mlflow", action="store_true")
    p.add_argument("--no-record", action="store_true", help="debug run: no RUN record")
    return p.parse_args(argv)


def build_context(run_id: str) -> JobContext:
    """Champion, profile, reference sample and every config the job reads."""
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    setup_tracking("training")
    model = load_alias(load_training_config().registry_model_name)
    return JobContext(
        run_id=run_id, model=model,
        version=f"credit-scoring@champion v{profile['model']['version']}",
        profile=profile, reference=load_partition("reference")[model_feature_columns()],
        contract=load_contract_config(), monitoring=load_monitoring_config(),
        alerts=load_alert_config(),
        quarantine_root=get_settings().data_dir / "quarantine" / "monitor" / run_id,
    )  # fmt: skip


def batch_inputs(scenario: str, limit: int) -> list[BatchInput]:
    """Batches of a generated scenario, in time order."""
    folder = get_settings().data_dir / "simulated" / scenario
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    items = [BatchInput(b["index"], b["batch_id"], b["issue_month"], folder / b["batch_id"])
             for b in manifest["batches"]]  # fmt: skip
    return items[:limit] if limit else items


def mlflow_key(flat: str) -> str:
    """``name{k=v}`` -> an MLflow-safe metric key ``name/v``."""
    if "{" not in flat:
        return flat
    name, labels = flat[:-1].split("{", 1)
    return name + "/" + "_".join(part.split("=", 1)[1] for part in labels.split(","))


def record(
    ctx: JobContext, state: BatchState, args: argparse.Namespace, experiment_id: str
) -> None:
    """Publish the batch: Pushgateway gauges and an MLflow child run."""
    with state.log.step("record"):
        samples = batch_samples(state, ctx.monitoring.get("feature_psi").sev1)
        if args.push:
            push(samples, get_settings().pushgateway_url, args.scenario)
        if not args.no_mlflow:
            with mlflow.start_run(run_name=state.batch_id, nested=True,
                                  experiment_id=experiment_id):  # fmt: skip
                mlflow.log_metrics({mlflow_key(k): v for k, v in as_dict(samples).items()})
                mlflow.set_tags({"batch_id": state.batch_id, "diagnosis": state.diagnosis,
                                 "severity": str(state.severity["level"])})  # fmt: skip


def summarize(states: list[BatchState]) -> dict[str, Any]:
    """Aggregates of a run: blocks, failures, alerts, diagnoses, durations."""
    fired: dict[str, int] = {}
    for s in states:
        for k, v in s.levels.items():
            fired[k] = max(fired.get(k, 0), v)
    durations = sorted(sum(s.log.durations_s().values()) for s in states)
    return {"batches": len(states),
            "blocked": sum(s.report.get("status") == "blocked" for s in states),
            "failed_steps": sum(len(s.log.failed()) for s in states),
            "alerts_max_level": active(fired),
            "diagnoses": dict(Counter(s.diagnosis for s in states)),
            "first_alert_batch": next((s.index for s in states if any(s.levels.values())), None),
            "duration_p50_s": durations[len(durations) // 2] if durations else None,
            "duration_max_s": durations[-1] if durations else None,
            **soft_rule_batches(states)}  # fmt: skip


def soft_rule_batches(states: list[BatchState]) -> dict[str, int]:
    """Batches in which each soft contract rule fired (``soft_<rule>``), for the RUN record."""
    counts = Counter(k for s in states for k in s.report.get("soft_warnings", {}))
    return {f"soft_{k}": n for k, n in sorted(counts.items())}


def run(args: argparse.Namespace, ctx: JobContext, experiment_id: str) -> dict[str, Any]:
    """Process every batch (sleeping ``interval`` between them) and return the summary."""
    mem, states = RunMemory(), []
    for i, item in enumerate(batch_inputs(args.scenario, args.limit)):
        if i and args.interval:
            time.sleep(args.interval)
        state = run_batch(ctx, item, mem)
        record(ctx, state, args, experiment_id)
        states.append(state)
    return summarize(states)


def log_parent_artifacts(paths: list[Path]) -> None:
    """Attach the run log, summary and the scenario's Evidently report to the parent run."""
    for path in paths:
        if path.exists():
            mlflow.log_artifact(str(path))


def _record_run(run_id: str, args: argparse.Namespace, summary: dict[str, Any], git) -> None:
    rec = RunRecord(
        run_id=run_id, kind="monitor", scenario=args.scenario, seed=0, data_hash="—",
        model="champion", mlflow_ref="experimento `monitoring`", sha=git[0], dirty=git[1],
        metrics={"job": {k: v for k, v in summary.items() if isinstance(v, int | float)}},
        verdict=(f"pipeline: {summary['batches']} lotes · {summary['blocked']} bloqueados · "
                 f"{summary['failed_steps']} etapas com falha · "
                 f"alertas {summary['alerts_max_level']}"),
        artifacts=[f"logs/{run_id}.jsonl", f"logs/{run_id}.summary.json"],
        extra={"modo": "replay" if args.interval else "lote a lote", "push": args.push},
    )  # fmt: skip
    write_record(rec)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    settings = get_settings()
    configure_logging(settings.log_level)
    args, git = parse_args(argv), git_state()
    run_id = (
        f"dev-{args.scenario}-{int(time.time())}"
        if args.no_record
        else next_run_id("monitor", args.scenario)
    )
    log_path: Path = settings.logs_dir / f"{run_id}.jsonl"
    handler = attach_run_log(log_path)
    ctx = build_context(run_id)  # loads the champion: MLflow points at `training` here
    exp_id = setup_tracking("monitoring")  # every run below goes to `monitoring`
    tracked = not args.no_mlflow
    with mlflow.start_run(run_name=run_id, experiment_id=exp_id) if tracked else nullcontext():
        summary = run(args, ctx, exp_id)
        summary_path = settings.logs_dir / f"{run_id}.summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if not args.no_mlflow:
            report = EVIDENTLY / f"{args.scenario}_evidently.html"
            log_parent_artifacts([summary_path, log_path, report])
    detach_run_log(handler)
    if not args.no_record:
        _record_run(run_id, args, summary, git)
    return 0


if __name__ == "__main__":
    sys.exit(main())
