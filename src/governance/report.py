"""``make fairness``: bias analysis in the normal regime and under the conservative mode (RUN).

Three views: group metrics of the champion on the 2013 test split; how much the model features
carry of the region (``addr_state``, kept out of the model); and, in the scenarios where the
conservative mode acts, the approval gaps of the plain champion, of the conservative mode
without the cap and of the current policy (cap of ADR-0015), with the value of each.
"""

import json
import sys
from typing import Any

import numpy as np
import pandas as pd

from src.config import get_settings
from src.data.features import model_feature_columns
from src.governance.fairness import (
    approval_gap,
    gaps,
    groups,
    load_fairness,
    proxy_strength,
    segment_table,
)
from src.governance.report_doc import EVIDENCE, fairness_record, write_doc
from src.logging_config import configure_logging
from src.models.dataset import load_partition
from src.reporting.run_record import git_state, next_run_id, write_record
from src.response import cli as rcli
from src.response import compare as cmp
from src.response.gate import scores

POLICY = "conservador com limite (política)"
# Discarded alternatives of ADR-0015 (None = no cap).
ALTERNATIVES = {
    "conservador sem limite": None,
    "limite só em home_ownership": ["home_ownership"],
    "limite nos três segmentos": ["home_ownership", "emp_length", "addr_state"],
}


def reference_section(ctx: dict[str, Any], cfg) -> dict[str, Any]:
    """Group metrics of the champion on the reference test split."""
    test = ctx["ref_test"].assign(score=lambda d: scores(ctx["champ"], d))
    approved = test["score"].to_numpy() < ctx["base"]
    out = {"rows": len(test), "approval_rate": float(approved.mean()), "segments": {}}
    for col, seg in cfg.segments.items():
        table = segment_table(test, approved, col, seg)
        out["segments"][col] = {"groups": table, "gaps": gaps(table, cfg.min_group_size)}
    return out


def _with_segments(pol, segments: list[str] | None):
    """Copy of the policy with another set of capped segments (None = no cap)."""
    cap = pol.conservative.fairness
    new = None if segments is None else cap.model_copy(update={"segments": segments})
    return pol.model_copy(
        update={"conservative": pol.conservative.model_copy(update={"fairness": new})}
    )


def deciders(ctx: dict[str, Any]) -> dict[str, cmp.Decider]:
    """Plain champion, the current policy and the discarded alternatives of ADR-0015."""
    pol, champ, base, cost = ctx["policy"], ctx["champ"], ctx["base"], ctx["cost"]
    out = {"champion puro": cmp.threshold_decider(champ, base)}
    for name, segments in ALTERNATIVES.items():
        out[name] = cmp.value_decider(champ, base, cost, _with_segments(pol, segments))
    out[POLICY] = cmp.value_decider(champ, base, cost, pol)
    return out


def run_decider(fn, periods, ctx: dict[str, Any], cfg) -> dict[str, Any]:
    """Value, per-batch approval gaps per segment and pooled home-ownership table of one decider."""
    value, per_batch, frames, approvals = 0.0, [], [], []
    for k, p in enumerate(periods):
        approved, _ = fn(p, k)
        value += cmp.value(p.frame, approved, ctx["cost"])["value"]
        per_batch.append({col: approval_gap(approved, groups(p.frame, col, seg).to_numpy(),
                                            cfg.min_batch_group_rows)
                          for col, seg in cfg.segments.items()} | {"batch": p.index})  # fmt: skip
        frames.append(p.frame.assign(score=scores(ctx["champ"], p.frame)))
        approvals.append(approved)
    pooled = pd.concat(frames, ignore_index=True)
    seg = cfg.segments["home_ownership"]
    table = segment_table(pooled, np.concatenate(approvals), "home_ownership", seg)
    return {"value": value, "per_batch": per_batch, "home_ownership": table}


def scenario_section(sid: str, ctx: dict[str, Any], cfg) -> dict[str, Any]:
    """The three decisions over the batches after the decision point of one scenario."""
    setup = rcli.scenario_setup(sid, ctx["policy"])
    runs = {n: run_decider(fn, setup["periods"], ctx, cfg) for n, fn in deciders(ctx).items()}
    base = runs["champion puro"]["value"]
    for r in runs.values():
        r["delta_vs_champion"] = r["value"] - base
    return {"scenario": sid, "decision_point": setup["t_d"], "strategies": runs}


def main() -> int:
    """Entry point."""
    configure_logging(get_settings().log_level)
    cfg, ctx, git = load_fairness(), rcli.context(), git_state()
    ref = load_partition("reference")
    proxy = proxy_strength(ref, model_feature_columns(), "addr_state")
    body = {"config": cfg.model_dump(), "reference": reference_section(ctx, cfg),
            "proxy_addr_state": dict(list(proxy.items())[:10]),
            "scenarios": [scenario_section(s, ctx, cfg) for s in cfg.scenarios]}  # fmt: skip
    json.dumps(body, allow_nan=False)
    run_id = write_record(fairness_record(body, next_run_id("fairness", "ALL"), git)).stem
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(
        json.dumps({"run_id": run_id, **body}, indent=2, ensure_ascii=False), "utf-8"
    )
    write_doc({"run_id": run_id, **body})
    return 0


if __name__ == "__main__":
    sys.exit(main())
