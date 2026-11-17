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

from src.governance.fairness import fairness_drift, load_fairness
from src.models.settings import load_cost_config
from src.models.threshold import loan_economics
from src.response.fairness_cap import relief
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


def _apply_cap(frame: pd.DataFrame, valid: pd.DataFrame, x: ChainInput, policy) -> pd.DataFrame:
    """ADR-0015: give back held applications until no group exceeds the approval-gap cap."""
    cap = policy.conservative.fairness
    if cap is None or not x.conservative or not len(frame):
        return frame
    held = frame["reason_code"].isin(["R10", "R11"]).to_numpy()
    approved = (frame["decision"] == "approve").to_numpy()
    labels = valid[cap.segment].astype("string").fillna("desconhecido").to_numpy()
    back = relief(approved, held, x.value, labels, cap)
    frame.loc[back, ["decision", "reason_code"]] = ["approve", "R12"]
    return frame


def _fairness(frame: pd.DataFrame, valid: pd.DataFrame, base: float) -> dict[str, Any] | None:
    """Fairness drift of the batch: approval gap of the decisions vs. the plain champion."""
    if not len(frame):
        return None
    policy = (frame["decision"] == "approve").to_numpy()
    return fairness_drift(valid, policy, valid["score"].to_numpy() < base, load_fairness())


def _tracking(frame: pd.DataFrame, k: float) -> float | None:
    """Expected bad rate of the approved loans with the corrected risk (vs. the 14% appetite)."""
    approved = frame[frame["decision"] == "approve"] if len(frame) else frame
    return float(np.minimum(1.0, k * approved["score"]).mean()) if len(approved) else None


def _summary(decision, mem: ResponseMemory, k: float, policy: PolicyConfig) -> dict[str, Any]:
    return {"rule": decision.rule_id, "situation": decision.situation,
            "auto": decision.codes("auto"), "human": decision.codes("human"),
            "conservative": mem.breaker.open, "risk_correction": k,
            "kill_switch": policy.kill_switch, "dry_run": policy.dry_run}  # fmt: skip


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
    frame = _apply_cap(frame, valid, x, policy)
    return frame, _summary(decision, mem, k, policy) | {
        "expected_bad_rate_approved": _tracking(frame, k),
        "fairness": _fairness(frame, valid, base),
        "decisions": {d: int(n) for d, n in frame["decision"].value_counts().items()}
        if len(frame)
        else {},
    }
