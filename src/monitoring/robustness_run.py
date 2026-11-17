"""``make robustness``: detector and responses over fresh seeds and magnitudes (RUN ``calib``).

Each variant goes through the same path as production, in memory: simulator → contract gate →
champion score → detector → evaluation against the variant's own ground truth. At the official
magnitude the response comparison also runs, so every US$ figure gets a spread over seeds.
Nothing is written under ``data/simulated/``.
"""

import json
import logging
import shutil
import sys
import time
from typing import Any

from src.config import get_settings
from src.contracts.gate import GateContext, run_gate
from src.contracts.settings import load_contract_config
from src.data.features import model_feature_columns
from src.logging_config import configure_logging
from src.models.dataset import load_partition
from src.monitoring.cli import EVIDENCE, scores_of, thresholds_sha, write_json
from src.monitoring.detect import Batch, DetectContext, detect_scenario
from src.monitoring.evaluation import evaluate
from src.monitoring.robustness import (
    RobustnessConfig,
    detection_row,
    detection_summary,
    load_robustness,
    response_summary,
    variant,
)
from src.monitoring.robustness_doc import robustness_record, write_doc
from src.monitoring.settings import load_monitoring_config
from src.reporting.run_record import git_state, next_run_id, write_record
from src.response import cli as rcli
from src.response import compare as cmp
from src.response.lifecycle import BatchView, TrainingRefusedError
from src.simulation.engine import SimContext, simulate
from src.simulation.manifest import ground_truth
from src.simulation.settings import ScenarioConfig, load_scenario

logger = logging.getLogger(__name__)
OUT = EVIDENCE / "robustness.json"


def shared_context() -> dict[str, Any]:
    """Champion, holdout, reference sample, detector, gate and response context, loaded once."""
    rctx = rcli.context()
    reference = load_partition("reference")[model_feature_columns()]
    reference = reference.assign(score=scores_of(rctx["champ"], reference))
    root = get_settings().data_dir / "quarantine" / "robustness"
    shutil.rmtree(root, ignore_errors=True)
    gate = GateContext(
        rctx["champ"],
        rctx["base"],
        "credit-scoring@champion (robustez)",
        rctx["profile"],
        load_contract_config(),
        root,
    )
    dctx = DetectContext(reference, rctx["profile"], load_monitoring_config())
    return {"rctx": rctx, "holdout": load_partition("holdout"), "gate": gate, "dctx": dctx}


def production_view(vcfg: ScenarioConfig, shared: dict[str, Any]) -> list[Batch]:
    """Batches of a variant as the job sees them: gated and scored."""
    champ = shared["rctx"]["champ"]
    sim = SimContext(
        vcfg, shared["holdout"], shared["rctx"]["profile"], lambda d: scores_of(champ, d)
    )
    out = []
    for b in simulate(sim):
        o = run_gate(b.applications, b.batch_id, shared["gate"])
        out.append(
            Batch(b.index, b.batch_id, b.issue_month, o.status, b.applications, o.scored, b.labels)
        )
    return out


def _runs(sid: str, setup: dict[str, Any], rctx: dict[str, Any]) -> tuple[list, dict]:
    st = rcli.strategies(setup, rctx)
    runs = [(n, setup["periods"], d) for n, d in st["deciders"].items()]
    if sid == "S4":
        try:
            runs += rcli.s4_extras(setup, rctx["champ"], rctx["base"], rctx["cfg"], rctx["profile"])
        except TrainingRefusedError as err:  # too few mature labels for the bugged challenger
            st["refused"]["retreinar sobre o dado com bug"] = str(err)
    return runs, st


def compare_setup(vcfg: ScenarioConfig, batches: list[Batch], results, t_d: int) -> dict:
    """The same setup ``make respond-compare`` builds, from in-memory batches."""
    periods = [
        cmp.Period(
            b.index, rcli.labeled_frame(b.applications, b.scored, b.labels), results[b.index]
        )
        for b in batches[t_d:]
    ]
    views = [BatchView(b.index, b.gate_status, b.applications, b.scored, b.labels) for b in batches]
    return {"batches": batches, "evidence": results, "t_d": t_d, "periods": periods,
            "views": views, "scenario": vcfg}  # fmt: skip


def response_row(sid: str, vcfg: ScenarioConfig, batches: list[Batch], results, rctx) -> dict:
    """Value of every response for one variant, as delta vs. doing nothing (US$)."""
    t_d, acts = cmp.decision_point(results, rctx["policy"])
    if t_d is None:
        return {"scenario": sid, "seed": vcfg.seed, "decision_point": None, "deltas": {}}
    runs, st = _runs(sid, compare_setup(vcfg, batches, results, t_d), rctx)
    recover = cmp.threshold_decider(rctx["champ"], rctx["base"])
    totals = {n: cmp.run_strategy(per, d, rctx["cost"], recover) for n, per, d in runs}
    base = totals.pop("não fazer nada")["value"]
    return {"scenario": sid, "seed": vcfg.seed, "decision_point": t_d, "policy_acts": acts,
            "gate_passed": bool(st["gate"]["passed"]), "refused": sorted(st["refused"]),
            "deltas": {n: t["value"] - base for n, t in totals.items()}}  # fmt: skip


def run_variant(sid: str, m: float, seed: int, cfg: RobustnessConfig, shared) -> tuple:
    """Detection row and (at the official magnitude) response row of one variant."""
    vcfg = variant(load_scenario(sid), 1.0 if sid == cfg.control else m, seed)
    batches = production_view(vcfg, shared)
    results = detect_scenario(shared["dctx"], batches)
    row = detection_row(sid, m, seed, results, evaluate(results, ground_truth(vcfg)))
    compare = sid in cfg.scenarios and m == cfg.compare_magnitude
    resp = response_row(sid, vcfg, batches, results, shared["rctx"]) if compare else None
    return row, resp


def grid(cfg: RobustnessConfig) -> list[tuple[str, float, int]]:
    """Every (scenario, magnitude, seed) of the study; the control varies only in seed."""
    cells = [(cfg.control, 0.0, s) for s in cfg.seeds]
    return cells + [(sid, m, s) for sid in cfg.scenarios for m in cfg.magnitudes for s in cfg.seeds]


def run_all(cfg: RobustnessConfig, shared: dict[str, Any]) -> tuple[list, list]:
    """Run the whole grid, logging progress."""
    det, resp, cells, start = [], [], grid(cfg), time.time()
    for i, (sid, m, seed) in enumerate(cells, 1):
        row, r = run_variant(sid, m, seed, cfg, shared)
        det.append(row)
        resp += [r] if r else []
        logger.info(
            "robustness variant",
            extra={
                "scenario": sid,
                "m": m,
                "seed": seed,
                "done": f"{i}/{len(cells)}",
                "elapsed_s": round(time.time() - start),
            },
        )
    return det, resp


def main() -> int:
    """Entry point."""
    configure_logging(get_settings().log_level)
    cfg, git = load_robustness(), git_state()
    det, resp = run_all(cfg, shared_context())
    body = {
        "config": cfg.model_dump(),
        "thresholds": thresholds_sha(),
        "detection": det,
        "cells": detection_summary(det, cfg),
        "responses": resp,
        "response_summary": response_summary([r for r in resp if r["deltas"]], cfg.reading),
    }
    json.dumps(body, allow_nan=False)  # fail before any RUN record is written
    run_id = write_record(robustness_record(body, next_run_id("calib", "ROBUST"), git)).stem
    write_json(OUT, {"run_id": run_id, **body})
    write_doc({"run_id": run_id, **body})
    return 0


if __name__ == "__main__":
    sys.exit(main())
