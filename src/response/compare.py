"""Response comparison (§7, caixa 7.9): what each answer to a degradation is worth.

From the decision point ``t_d`` (first batch where the response matrix asks for something
beyond logging), each strategy decides every later batch; decisions are valued with the
realized simulated outcomes and the ADR-0016 economics (good approved: +gain, bad approved:
-loss, rejected or in review: 0). Strategies that need labels or training use only what is
observable at ``t_d`` (GR-7, GR-8) and start at ``t_d + 1``.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.governance.fairness import load_fairness
from src.models.settings import CostConfig
from src.models.threshold import loan_economics
from src.response.fairness_cap import relieve
from src.response.gate import scores
from src.response.guardrails import (
    BreakerState,
    expected_value,
    review_overflow,
    risk_correction,
)  # fmt: skip
from src.response.policy import PolicyFacts, decide
from src.response.settings import PolicyConfig

SIGNALS_L34 = ("score_psi", "approval_delta_pp", "bad_rate_ratio", "auc_drop")
CAP_FLOOR = 0.05


@dataclass
class Period:
    """One batch from the decision point on, with what the strategies need."""

    index: int
    frame: pd.DataFrame  # applications + realized target (and true X when a bug was fixed)
    evidence: dict[str, Any]  # detector result of the batch (severity, diagnosis, l4)


def facts_of(ev: dict[str, Any]) -> PolicyFacts:
    """Policy facts from a detector result (signal levels stand for the alert levels)."""
    s = ev["severity"]["signals"]
    return PolicyFacts(ev["diagnosis"], ev["severity"]["level"], max(s[k] for k in SIGNALS_L34))


def decision_point(evidence: list[dict[str, Any]], policy: PolicyConfig) -> tuple[int | None, bool]:
    """First batch whose rule asks for more than registering (A0), and whether the policy acts.

    When the matrix never acts (benign drift), the first alert is used as a what-if point.
    """
    for ev in evidence:
        if set(decide(facts_of(ev), policy).codes()) - {"A0"}:
            return ev["index"], True
    first = next((ev["index"] for ev in evidence if ev["severity"]["level"] >= 1), None)
    return first, False


def value(frame: pd.DataFrame, approved: np.ndarray, cost: CostConfig) -> dict[str, float]:
    """Realized value of a set of approvals, with volume and bad rate."""
    gain, loss = loan_economics(frame, cost)
    y = frame["target"].to_numpy(int)
    v = np.where(y == 1, -loss, gain) * approved
    return {"value": float(v.sum()), "apps": float(len(y)), "approved": float(approved.sum()),
            "bad_approved": float((y * approved).sum())}  # fmt: skip


Decider = Callable[[Period, int], tuple[np.ndarray, np.ndarray]]  # (approved, review)


def run_strategy(
    periods: list[Period], decide_fn: Decider, cost: CostConfig, recover: Decider
) -> dict[str, float]:
    """Sum the realized value of a strategy over every period.

    ``value`` treats an application in review as lost (0). ``value_review_recovered`` assumes
    the review later decides it as ``recover`` would (the champion on the data available then):
    the two bound the cost of sending cases to review.
    """
    total = {"value": 0.0, "apps": 0.0, "approved": 0.0, "bad_approved": 0.0, "review": 0.0,
             "value_review_recovered": 0.0}  # fmt: skip
    for k, period in enumerate(periods):
        approved, review = decide_fn(period, k)
        for key, val in value(period.frame, approved, cost).items():
            total[key] += val
        total["review"] += float(review.sum())
        later = approved | (review & recover(period, k)[0])
        total["value_review_recovered"] += value(period.frame, later, cost)["value"]
    return total


def _breaker_open(breaker: BreakerState, state: dict, period: Period, policy: PolicyConfig,
                  k: int, forced: bool) -> bool:  # fmt: skip
    """Track the last mature ratio and move the breaker exactly as the job does."""
    if period.evidence["l4"]:
        state["ratio"] = period.evidence["l4"]["bad_rate_ratio"]
    breaker.update(forced or decide(facts_of(period.evidence), policy).wants_conservative,
                   policy, k)  # fmt: skip
    return breaker.open


def value_decider(champion: Any, base: float, cost: CostConfig, policy: PolicyConfig,
                  forced: bool = False, correct: bool = True) -> Decider:  # fmt: skip
    """Conservative mode by value (ADR-0019): what the champion approves with a non-positive
    expected value under the corrected risk goes to review. ``correct=False`` keeps k = 1, to
    separate the effect of the per-loan rule from the effect of the risk correction."""
    breaker, state = BreakerState(), {"ratio": None}

    def fn(period: Period, k: int):
        p = scores(champion, period.frame)
        if not _breaker_open(breaker, state, period, policy, k, forced):
            return p < base, np.zeros(len(p), bool)
        gain, loss = loan_economics(period.frame, cost)
        factor = risk_correction(state["ratio"], policy.conservative) if correct else 1.0
        ev = expected_value(p, gain, loss, factor)
        held = (p < base) & (ev <= 0)
        over = review_overflow(held, ev, policy.conservative.capacity(len(p)))
        approved, review = (p < base) & ~held, held & ~over
        cap = policy.conservative.fairness
        if cap is not None:  # ADR-0015, same rule as the job
            back = relieve(approved, held, ev, period.frame, cap, load_fairness().segments)
            approved, review = approved | back, review & ~back
        return approved, review

    return fn


def cap_threshold(p: np.ndarray, base: float, appetite: float, k: float) -> float:
    """Discarded alternative (ADR-0019): largest threshold whose corrected bad rate fits the cap."""
    risk = np.minimum(1.0, k * p)
    for t in np.round(np.arange(base, CAP_FLOOR - 1e-9, -0.005), 6):
        if (p < t).any() and risk[p < t].mean() <= appetite:
            return float(t)
    return CAP_FLOOR


def cap_decider(champion: Any, base: float, appetite: float, policy: PolicyConfig) -> Decider:
    """Conservative mode by the 14% bad-rate cap (ADR-0012 item 3, superseded by ADR-0019)."""
    breaker, state = BreakerState(), {"ratio": None}

    def fn(period: Period, k: int):
        p = scores(champion, period.frame)
        if not _breaker_open(breaker, state, period, policy, k, False):
            return p < base, np.zeros(len(p), bool)
        t_c = cap_threshold(p, base, appetite, risk_correction(state["ratio"], policy.conservative))
        return p < t_c, (p >= t_c) & (p < base)

    return fn


def threshold_decider(model: Any, base: float, start: int = 0, fallback: Any = None) -> Decider:
    """Approve below ``base``; ``model`` applies from period ``start`` on (``fallback`` before)."""

    def fn(period: Period, k: int):
        m = model if k >= start or fallback is None else fallback
        approved = scores(m, period.frame) < base
        return approved, np.zeros(len(approved), bool)

    return fn


def summarize(name: str, total: dict[str, float], baseline: float | None) -> dict[str, Any]:
    """Row of the comparison table."""
    apps = max(total["apps"], 1.0)
    return {"strategy": name, "value": total["value"], "value_per_app": total["value"] / apps,
            "approval_rate": total["approved"] / apps, "review_rate": total["review"] / apps,
            "bad_rate_approved": total["bad_approved"] / max(total["approved"], 1.0),
            "delta_vs_nothing": None if baseline is None else total["value"] - baseline,
            "value_review_recovered": total["value_review_recovered"]}  # fmt: skip
