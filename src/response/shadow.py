"""Shadow evaluation (A6) and the promotion/rollback drill (GR-5, GR-6).

The challenger scores the same batches as the champion without deciding anything. Each time
labels mature, both are compared on them and the gate is re-run: the first batch where the
gate passes is when a human could promote (A7). The drill then exercises promotion and
rollback on a separate registry model, never on the real champion.
"""

from typing import Any

import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src.response.gate import evaluate_gate, scores
from src.response.lifecycle import LifecycleConfig
from src.response.registry_ops import alias_version, promote, register, rollback


def _matured(batches, t: int) -> pd.DataFrame:
    """Validated rows whose labels become observable at ``t``."""
    parts = []
    for b in batches:
        lab = b.labels[(b.labels["label_batch"] == t) & b.labels["target"].notna()]
        valid = b.applications[b.applications["loan_key"].isin(b.scored["loan_key"])]
        parts.append(valid.merge(lab[["loan_key", "target"]], on="loan_key"))
    rows = [p for p in parts if len(p)]
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _compare(champion: Any, challenger: Any, rows: pd.DataFrame) -> dict[str, float]:
    y = rows["target"].astype(int).to_numpy()
    pc, pk = scores(champion, rows), scores(challenger, rows)
    return {"rows": float(len(y)), "auc_champion": float(roc_auc_score(y, pc)),
            "auc_challenger": float(roc_auc_score(y, pk)),
            "ratio_champion": float(y.mean() / pc.mean()),
            "ratio_challenger": float(y.mean() / pk.mean())}  # fmt: skip


def shadow_timeline(
    batches, t_train: int, champion: Any, challenger: Any, ctx: dict[str, Any]
) -> list[dict[str, Any]]:
    """Per later batch: shadow approvals; on maturing labels, the comparison and the gate."""
    timeline = []
    for b in batches[t_train + 1 :]:
        valid = b.applications[b.applications["loan_key"].isin(b.scored["loan_key"])]
        base = ctx["base"]
        row = {"batch": b.index,
               "approval_champion": float(np.mean(scores(champion, valid) < base)),
               "approval_challenger": float(np.mean(scores(challenger, valid) < base))}  # fmt: skip
        matured = _matured(batches, b.index)
        if len(matured) and matured["target"].nunique() == 2:
            row["matured"] = _compare(champion, challenger, matured)
            gate = evaluate_gate(
                champion, challenger, matured, ctx["ref_test"], ctx["base"], ctx["cfg"]
            )
            row["gate_passed"] = gate["passed"]
            row["gate_checks"] = {k: v["passed"] for k, v in gate["checks"].items()}
        timeline.append(row)
    return timeline


def drill(champion: Any, challenger: Any, cfg: LifecycleConfig, trusted: list[str]) -> dict:
    """Register both on the drill model, promote the challenger, then roll back (twice)."""
    name, previous = cfg.registry["drill_model_name"], cfg.registry["previous_alias"]
    with mlflow.start_run(run_name="drill-promote-rollback"):
        v_champ, v_chall = register(champion, name, trusted), register(challenger, name, trusted)
    mlflow.MlflowClient().set_registered_model_alias(name, "champion", v_champ)
    steps = [{"step": "inicial", "champion": alias_version(name, "champion")}]
    steps.append({"step": "promoção (A7)", **promote(name, v_chall, previous)})
    steps.append({"step": "rollback (GR-6)", **rollback(name, previous)})
    restored = alias_version(name, "champion") == v_champ
    steps.append({"step": "rollback do rollback", **rollback(name, previous)})
    return {"model": name, "versions": {"champion_copy": v_champ, "challenger": v_chall},
            "steps": steps, "rollback_restored_previous": restored,
            "rollback_reversible": alias_version(name, "champion") == v_chall}  # fmt: skip
