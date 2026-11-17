"""``respond`` step of the job: policy matrix → circuit breaker → guardrail chain → decisions.

The policy file is read on every batch, so flipping the kill switch or the conservative-mode
override takes effect on the next batch without a deploy (GR-9). In ``dry_run`` the actions
are computed and logged, but the decisions stay those of the plain champion. The conservative
mode is by expected value with the risk corrected (ADR-0019); the 14% bad-rate appetite is
reported as a tracking metric, not used as a cut.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.models.settings import load_cost_config
from src.models.threshold import loan_economics
from src.response.guardrails import (
    BreakerState,
    ChainInput,
    decisions_frame,
    expected_value,
    risk_correction,
)  # fmt: skip
from src.response.policy import PolicyFacts, decide, output_level
from src.response.settings import PolicyConfig, load_policy


@dataclass
class ResponseMemory:
    """Response state carried across batches."""

    breaker: BreakerState = field(default_factory=BreakerState)
    last_ratio: float | None = None


def _chain_input(
    valid: pd.DataFrame, base: float, decision, mem: ResponseMemory, policy: PolicyConfig
) -> tuple[ChainInput, float]:
    scores = valid["score"].to_numpy(float) if len(valid) else np.empty(0)
    k = risk_correction(mem.last_ratio, policy.conservative)
    gain, loss = loan_economics(valid, load_cost_config()) if len(valid) else (scores, scores)
    live, ev = not policy.dry_run, expected_value(scores, gain, loss, k)
    x = ChainInput(scores, base, ev <= 0, kill_switch=live and policy.kill_switch,
                   quarantine=live and decision.wants_quarantine,
                   conservative=live and mem.breaker.open, value=ev,
                   review_capacity=policy.conservative.capacity(len(scores)))  # fmt: skip
    return x, k


def _tracking(frame: pd.DataFrame, k: float) -> float | None:
    """Expected bad rate of the approved loans with the corrected risk (vs. the 14% appetite)."""
    approved = frame[frame["decision"] == "approve"] if len(frame) else frame
    return float(np.minimum(1.0, k * approved["score"]).mean()) if len(approved) else None


def respond(
    t: int, valid: pd.DataFrame, signals: dict[str, Any], mem: ResponseMemory, base: float
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Decide the batch. ``valid`` = scored rows with their application fields and ``score``."""
    policy = load_policy()
    if signals.get("bad_rate_ratio") is not None:
        mem.last_ratio = float(signals["bad_rate_ratio"])
    facts = PolicyFacts(signals["diagnosis"], signals["batch_level"],
                        output_level(signals["levels"], policy))  # fmt: skip
    decision = decide(facts, policy)
    mem.breaker.update(decision.wants_conservative, policy, t)
    x, k = _chain_input(valid, base, decision, mem, policy)
    frame = decisions_frame(valid["loan_key"], x) if len(valid) else pd.DataFrame()
    counts = frame["decision"].value_counts().to_dict() if len(frame) else {}
    return frame, {"rule": decision.rule_id, "situation": decision.situation,
                   "auto": decision.codes("auto"), "human": decision.codes("human"),
                   "conservative": mem.breaker.open, "risk_correction": k,
                   "expected_bad_rate_approved": _tracking(frame, k),
                   "kill_switch": policy.kill_switch, "dry_run": policy.dry_run,
                   "decisions": {key: int(v) for key, v in counts.items()}}  # fmt: skip
