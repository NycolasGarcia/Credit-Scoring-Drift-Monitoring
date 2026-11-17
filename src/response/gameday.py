"""``make gameday``: the job batch by batch, as the on-call operator sees it (§11.7).

The operator view of a batch has only what the dashboard and the logs show: contract status,
failed steps, alerts and their severity, diagnosis, output and matured-label signals, and the
policy decision. Nothing from the scenario manifest. With ``--until-sev`` the run stops after
the first batch at that severity, which is when the incident is opened; the job is
deterministic, so running again with a larger ``--limit`` is the same as letting it continue.
``--shadow-at T`` is the human A6 of the playbook (ADR-0022): train the challenger with what is
observable at batch T (GR-7, GR-8) and shadow it on the following batches.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, get_settings
from src.logging_config import configure_logging
from src.observability.runner import batch_inputs, build_context
from src.observability.samples import BatchState
from src.pipeline import RunMemory, run_batch
from src.reporting.run_record import RunRecord, git_state, next_run_id, write_record
from src.response import cli, shadow
from src.response.lifecycle import TrainingRefusedError, challenger_rows, train_challenger

logger = logging.getLogger(__name__)
EVIDENCE = PROJECT_ROOT / "docs" / "evidence" / "response"


def _r(v: Any) -> Any:
    return round(float(v), 4) if isinstance(v, int | float) and not isinstance(v, bool) else v


def operator_view(s: BatchState) -> dict[str, Any]:
    """What the operator can see about one batch (no ground truth)."""
    l4, r = s.l4 or {}, s.response
    return {"batch": s.index, "issue_month": s.issue_month, "gate": s.report.get("status"),
            "failed_steps": s.log.failed(),
            "alerts": {k: v for k, v in sorted(s.levels.items()) if v},
            "max_level": max(s.levels.values(), default=0), "diagnosis": s.diagnosis,
            "score_psi": _r(s.l3.get("score_psi")), "approval_rate": _r(s.l3.get("approval_rate")),
            "bad_rate_ratio": _r(l4.get("bad_rate_ratio")), "auc_mature": _r(l4.get("auc")),
            "segment_feature": l4.get("segment_feature"), "segment_gap": _r(l4.get("segment_gap")),
            "rule": r.get("rule"), "auto": r.get("auto"), "human": r.get("human"),
            "conservative": r.get("conservative"), "risk_correction": _r(r.get("risk_correction")),
            "decisions": r.get("decisions")}  # fmt: skip


def watch(scenario: str, run_id: str, until_sev: int, limit: int) -> list[dict[str, Any]]:
    """Run the job over the scenario; stop after the first batch at ``until_sev`` (0 = never)."""
    ctx, mem, views = build_context(run_id), RunMemory(), []
    for item in batch_inputs(scenario, limit):
        view = operator_view(run_batch(ctx, item, mem))
        views.append(view)
        logger.info("gameday_batch", extra={"run_id": run_id, **view})
        if until_sev and view["max_level"] >= until_sev:
            break
    return views


def shadow_at(scenario: str, t: int, limit: int) -> list[dict[str, Any]]:
    """A6 by hand: challenger trained at batch ``t``, shadowed up to ``limit`` batches."""
    ctx = cli.context()
    setup = cli.scenario_setup(scenario, ctx["policy"])
    try:
        challenger, _ = train_challenger(challenger_rows(setup["views"], t, ctx["cfg"]), ctx["cfg"])
    except TrainingRefusedError as err:  # GR-7/GR-8: the refusal is the answer
        return [{"batch": t, "refused": str(err)}]
    batches = setup["batches"][: limit or None]
    return shadow.shadow_timeline(batches, t, ctx["champ"], challenger, ctx)


def gameday_record(scenario: str, views: list[dict[str, Any]], run_id: str, git) -> RunRecord:
    """RUN record (kind ``gameday``) of the full run, for the incident timeline."""
    first = {lvl: next((v["batch"] for v in views if v["max_level"] >= lvl), None)
             for lvl in (1, 2, 3)}  # fmt: skip
    on = next((v["batch"] for v in views if v["conservative"]), None)
    metrics = {f"lote {v['batch']}": {"nível": float(v["max_level"]),
               "aprovação": v["approval_rate"] or 0.0, "razão obs/esp": v["bad_rate_ratio"] or 0.0,
               "conservador": float(bool(v["conservative"]))} for v in views}  # fmt: skip
    return RunRecord(
        run_id=run_id, kind="gameday", scenario=scenario, seed=0, data_hash="—",
        model="champion", mlflow_ref="—", metrics=metrics, sha=git[0], dirty=git[1],
        verdict=(f"primeiro SEV-1 no lote {first[1]} · primeiro SEV-2 no lote {first[2]} · "
                 f"modo conservador desde o lote {on}"),
        artifacts=[f"docs/evidence/response/gameday_{scenario}.json"],
        notes=["Visão do operador: só alertas, diagnóstico e decisão da política, sem manifesto."],
    )  # fmt: skip


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """CLI arguments."""
    p = argparse.ArgumentParser(description="Game day: the job as the operator sees it.")
    p.add_argument("--scenario", default="S2")
    p.add_argument("--until-sev", type=int, default=0, help="stop after the first batch at it")
    p.add_argument("--limit", type=int, default=0, help="process only the first N batches")
    p.add_argument("--out", type=Path, help="operator view of a triage run (default: logs/)")
    p.add_argument("--record", action="store_true", help="full run: evidence and RUN record")
    p.add_argument("--shadow-at", type=int, help="A6: train the challenger at this batch")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    configure_logging(get_settings().log_level)
    args, git = parse_args(argv), git_state()
    run_id = (next_run_id("gameday", args.scenario) if args.record
              else f"gameday-{args.scenario}-{int(time.time())}")  # fmt: skip
    if args.shadow_at is not None:
        views = shadow_at(args.scenario, args.shadow_at, args.limit)
    else:
        views = watch(args.scenario, run_id, args.until_sev, args.limit)
    body = json.dumps({"run_id": run_id, "batches": views}, indent=2, ensure_ascii=False,
                      allow_nan=False)  # fmt: skip
    if args.record:
        write_record(gameday_record(args.scenario, views, run_id, git))
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        (EVIDENCE / f"gameday_{args.scenario}.json").write_text(body, "utf-8")
    else:
        out = args.out or get_settings().logs_dir / f"{run_id}.view.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, "utf-8")
        logger.info("gameday_view", extra={"path": str(out), "batches": len(views)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
