"""``make respond-compare`` (caixa 7.9) and ``make rollback`` (GR-6)."""

import argparse
import json
import logging
import sys
from typing import Any

import numpy as np
import pandas as pd

from src.config import PROJECT_ROOT
from src.contracts.schema import to_application_batch
from src.logging_config import configure_logging
from src.models.dataset import internal_split, load_partition
from src.models.registry import setup_tracking
from src.models.settings import load_cost_config, load_training_config
from src.monitoring.cli import champion, load_batches
from src.reporting.run_record import git_state, next_run_id, write_record
from src.response import compare as cmp
from src.response import docs
from src.response.gate import evaluate_gate
from src.response.lifecycle import (
    BatchView,
    TrainingRefusedError,
    challenger_rows,
    fit_recalibration,
    load_lifecycle,
    recalibration_rows,
    train_challenger,
)  # fmt: skip
from src.response.registry_ops import rollback
from src.response.settings import load_policy
from src.simulation.engine import SimContext, simulate_batch
from src.simulation.settings import load_scenario

logger = logging.getLogger(__name__)
EVIDENCE = PROJECT_ROOT / "docs" / "evidence" / "response"
DRIFT = PROJECT_ROOT / "docs" / "evidence" / "drift"
SCENARIOS = ("S1", "S2", "S3", "S4")


def _frame(apps: pd.DataFrame, scored: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    valid = apps[apps["loan_key"].isin(scored["loan_key"])]
    return valid.merge(labels[["loan_key", "target"]], on="loan_key")


def true_frames(sid: str, batches, model, profile, t_d: int) -> list[pd.DataFrame]:
    """S4 with the source fixed: the same rows rebuilt without the unit bug (determinism)."""
    cfg = load_scenario(sid)
    clean = cfg.model_copy(
        update={"transforms": [t for t in cfg.transforms if t.kind != "unit_bug"]}
    )
    ctx = SimContext(clean, load_partition("holdout"), profile,
                     lambda d: cmp.scores(model, d))  # fmt: skip
    out = []
    for b in batches[t_d:]:
        sim = simulate_batch(ctx, b.index)
        out.append(_frame(to_application_batch(sim.applications), b.scored, b.labels))
    return out


def scenario_setup(sid: str, policy) -> dict[str, Any]:
    """Batches, detector evidence, decision point, periods and training views of one scenario."""
    _, batches = load_batches(sid)
    evidence = json.loads((DRIFT / f"{sid}.json").read_text(encoding="utf-8"))["batches"]
    t_d, acts = cmp.decision_point(evidence, policy)
    periods = [cmp.Period(b.index, _frame(b.applications, b.scored, b.labels), evidence[b.index])
               for b in batches[t_d:]]  # fmt: skip
    views = [BatchView(b.index, b.gate_status, b.applications, b.scored, b.labels) for b in batches]
    return {"batches": batches, "evidence": evidence, "t_d": t_d, "periods": periods,
            "views": views, "policy_acts": acts}  # fmt: skip


def strategies(setup: dict, ctx: dict) -> dict:
    """Every response to compare, as deciders, plus the gate verdict of the challenger."""
    t_d, views = setup["t_d"], setup["views"]
    champ, base, cfg, policy = ctx["champ"], ctx["base"], ctx["cfg"], ctx["policy"]
    appetite, ref_test = ctx["appetite"], ctx["ref_test"]
    refused: dict[str, str] = {}
    try:
        recal = fit_recalibration(champ, recalibration_rows(views, t_d, cfg), cfg)
    except TrainingRefusedError as err:  # GR-8: stays with the champion
        recal, refused["recalibrar (A5)"] = champ, str(err)
    try:
        challenger, recent = train_challenger(challenger_rows(views, t_d, cfg), cfg)
        gate = evaluate_gate(champ, challenger, recent, ref_test, base, cfg)
    except TrainingRefusedError as err:
        challenger, gate, refused["retreinar"] = champ, {"passed": False, "checks": {}}, str(err)
    promoted = challenger if gate["passed"] else champ
    cost = ctx["cost"]
    return {"deciders": {
        "não fazer nada": cmp.threshold_decider(champ, base),
        "modo conservador por valor (política)": cmp.value_decider(champ, base, cost, policy),
        "modo conservador por valor, forçado": cmp.value_decider(champ, base, cost, policy, True),
        "teto de 14% (descartado, ADR-0019)": cmp.cap_decider(champ, base, appetite, policy),
        "recalibrar (A5)": cmp.threshold_decider(recal, base, start=1, fallback=champ),
        "retreinar com gate (A6+GR-5)": cmp.threshold_decider(promoted, base, 1, champ),
        "retreinar sem gate": cmp.threshold_decider(challenger, base, start=1, fallback=champ),
    }, "gate": gate, "refused": refused,
       "recalibration": {k: getattr(recal, k, None) for k in ("a", "b")}}  # fmt: skip


def s4_extras(setup: dict, champ, base: float, cfg, profile) -> list[tuple[str, list, Any]]:
    """Fix the source (hold t_d, then the true data) and retrain on the bugged data."""
    t_d, views = setup["t_d"], setup["views"]
    fixed = [cmp.Period(p.index, f, p.evidence) for p, f in
             zip(setup["periods"], true_frames("S4", setup["batches"], champ, profile, t_d),
                 strict=True)]  # fmt: skip

    def held_then_fixed(period, k):
        p = cmp.scores(champ, period.frame)
        return (p < base) & (k > 0), np.full(len(p), k == 0)

    late = t_d + 4  # labels of the first bugged cohorts are mature by now (lag 3)
    bugged, _ = train_challenger(challenger_rows(views, late, cfg), cfg)
    return [
        ("quarentena e corrigir a fonte", fixed, held_then_fixed),
        (
            "retreinar sobre o dado com bug",
            setup["periods"],
            cmp.threshold_decider(bugged, base, start=late - t_d + 1, fallback=champ),
        ),
    ]


def compare_scenario(sid: str, ctx: dict) -> dict[str, Any]:
    """Comparison table of one scenario."""
    setup = scenario_setup(sid, ctx["policy"])
    st = strategies(setup, ctx)
    runs = [(n, setup["periods"], d) for n, d in st["deciders"].items()]
    if sid == "S4":
        runs += s4_extras(setup, ctx["champ"], ctx["base"], ctx["cfg"], ctx["profile"])
    recover = cmp.threshold_decider(ctx["champ"], ctx["base"])
    totals = {n: cmp.run_strategy(per, d, ctx["cost"], recover) for n, per, d in runs}
    base_value = totals["não fazer nada"]["value"]
    rule = cmp.decide(cmp.facts_of(setup["evidence"][setup["t_d"]]), ctx["policy"])
    return {"scenario": sid, "decision_point": setup["t_d"], "batches": len(setup["periods"]),
            "policy_acts": setup["policy_acts"], "refused": st["refused"],
            "rule": rule.rule_id, "situation": rule.situation, "actions": rule.codes(),
            "gate": st["gate"], "recalibration": st["recalibration"],
            "rows": [cmp.summarize(n, t, base_value) for n, t in totals.items()]}  # fmt: skip


def reference_test() -> pd.DataFrame:
    """2013 test split used by the gate (same split as training)."""
    return internal_split(load_partition("reference"), load_training_config())["test"]


def run_compare(git: tuple[str, bool]) -> None:
    """Compare responses on every scenario with known outcomes; write evidence and a RUN record."""
    cost = load_cost_config()
    profile = json.loads((PROJECT_ROOT / "models" / "reference_profile.json").read_text("utf-8"))
    ctx = {"champ": champion(), "base": profile["threshold"], "cfg": load_lifecycle(),
           "policy": load_policy(), "appetite": cost.risk_appetite.max_bad_rate_approved,
           "cost": cost, "profile": profile,
           "ref_test": reference_test()}  # fmt: skip
    results = [compare_scenario(s, ctx) for s in SCENARIOS]
    json.dumps(results, allow_nan=False)
    rec = docs.compare_record(results, next_run_id("response", "ALL"), git)
    run_id = write_record(rec).stem
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    body = {"run_id": run_id, "scenarios": results}
    (EVIDENCE / "compare.json").write_text(json.dumps(body, indent=2, ensure_ascii=False), "utf-8")
    docs.write_doc(body)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    configure_logging()
    p = argparse.ArgumentParser(description="Response comparison and rollback.")
    p.add_argument("command", choices=["compare", "rollback"])
    p.add_argument("--registry", default=load_training_config().registry_model_name)
    args = p.parse_args(argv)
    if args.command == "rollback":
        setup_tracking("response")
        aliases = rollback(args.registry, load_lifecycle().registry["previous_alias"])
        logger.info("rollback", extra={"registry": args.registry, **aliases})
        return 0
    run_compare(git_state())
    return 0


if __name__ == "__main__":
    sys.exit(main())
