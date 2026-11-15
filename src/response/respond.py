"""``respond`` step of the job: policy matrix → circuit breaker → guardrail chain → decisions.

The policy file is read on every batch, so flipping the kill switch or the conservative-mode
override takes effect on the next batch without a deploy (GR-9). In ``dry_run`` the actions
are computed and logged, but the decisions stay those of the plain champion.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.models.settings import load_cost_config
from src.response.guardrails import BreakerState, ChainInput, decisions_frame, policy_threshold
from src.response.policy import PolicyFacts, decide, output_level
from src.response.settings import load_policy


@dataclass
class ResponseMemory:
    """Response state carried across batches."""

    breaker: BreakerState = field(default_factory=BreakerState)
    last_ratio: float | None = None


def _chain_input(scored: pd.DataFrame, base: float, decision, mem, policy) -> ChainInput:
    appetite = load_cost_config().risk_appetite.max_bad_rate_approved
    scores = scored["score"].to_numpy(float) if len(scored) else np.empty(0)
    t_c = policy_threshold(scores, base, appetite, mem.last_ratio, policy.conservative)
    live = not policy.dry_run
    return ChainInput(scores, base, t_c, kill_switch=live and policy.kill_switch,
                      quarantine=live and decision.wants_quarantine,
                      conservative=live and mem.breaker.open)  # fmt: skip


def respond(
    t: int, scored: pd.DataFrame, signals: dict[str, Any], mem: ResponseMemory, base: float
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Decide the batch. ``signals`` carries diagnosis, batch level, alert levels and L4 ratio."""
    policy = load_policy()
    if signals.get("bad_rate_ratio") is not None:
        mem.last_ratio = float(signals["bad_rate_ratio"])
    facts = PolicyFacts(signals["diagnosis"], signals["batch_level"],
                        output_level(signals["levels"], policy))  # fmt: skip
    decision = decide(facts, policy)
    mem.breaker.update(decision.wants_conservative, policy, t)
    x = _chain_input(scored, base, decision, mem, policy)
    frame = decisions_frame(scored["loan_key"], x) if len(scored) else pd.DataFrame()
    counts = frame["decision"].value_counts().to_dict() if len(frame) else {}
    return frame, {"rule": decision.rule_id, "situation": decision.situation,
                   "auto": decision.codes("auto"), "human": decision.codes("human"),
                   "conservative": mem.breaker.open, "policy_threshold": x.policy_threshold,
                   "kill_switch": policy.kill_switch, "dry_run": policy.dry_run,
                   "decisions": {k: int(v) for k, v in counts.items()}}  # fmt: skip
