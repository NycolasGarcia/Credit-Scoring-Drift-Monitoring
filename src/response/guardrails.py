"""Decision guardrails as a Chain of Responsibility (GR-9 → A2 → GR-4 → base threshold).

Each handler decides the rows it owns and passes the rest down the chain. Every decision
carries a reason code, so a human reviewer (and the applicant) can know why it was made.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.response.settings import Conservative, PolicyConfig

REASONS = {
    "R00": "aprovado: score abaixo do limiar do champion",
    "R01": "recusado: score acima do limiar do champion",
    "R10": "revisão humana: modo conservador, valor esperado não positivo com o risco corrigido",
    "R20": "revisão humana: decisão automática suspensa (kill switch)",
    "R30": "revisão humana: lote em quarentena preventiva (suspeita de dado quebrado)",
}


@dataclass
class BreakerState:
    """Circuit breaker of the conservative mode (GR-4), with cool-down hysteresis."""

    open: bool = False
    quiet: int = 0
    opened_at: int | None = None

    def update(self, wants: bool, policy: PolicyConfig, t: int) -> None:
        """Open on request, close after ``cool_down_batches`` quiet batches; human override wins."""
        if policy.conservative_mode != "auto":
            self.open = policy.conservative_mode == "on"
            return
        if wants:
            self.opened_at = t if not self.open else self.opened_at
            self.open, self.quiet = True, 0
        elif self.open:
            self.quiet += 1
            if self.quiet >= policy.cool_down_batches:
                self.open, self.quiet, self.opened_at = False, 0, None


def risk_correction(ratio: float | None, cfg: Conservative) -> float:
    """Factor applied to the champion's risk: the last mature observed/expected ratio, if > 1."""
    return max(1.0, ratio) if cfg.use_mature_ratio and ratio else 1.0


def negative_value(
    scores: np.ndarray, gain: np.ndarray, loss: np.ndarray, correction: float
) -> np.ndarray:
    """Loans whose expected value is not positive once the risk is corrected (ADR-0019)."""
    risk = np.minimum(1.0, correction * scores)
    return (1 - risk) * gain - risk * loss <= 0


@dataclass(frozen=True)
class ChainInput:
    """Everything the chain needs for one batch."""

    scores: np.ndarray
    base_threshold: float
    negative_value: np.ndarray
    kill_switch: bool
    quarantine: bool
    conservative: bool


Handler = Callable[[ChainInput], tuple[np.ndarray, str, str] | None]


def _kill_switch(x: ChainInput):
    return (np.ones(len(x.scores), bool), "review", "R20") if x.kill_switch else None


def _quarantine(x: ChainInput):
    return (np.ones(len(x.scores), bool), "review", "R30") if x.quarantine else None


def _conservative(x: ChainInput):
    if not x.conservative:
        return None
    return x.negative_value & (x.scores < x.base_threshold), "review", "R10"


def _reject(x: ChainInput):
    return x.scores >= x.base_threshold, "reject", "R01"


def _approve(x: ChainInput):
    return np.ones(len(x.scores), bool), "approve", "R00"


CHAIN: tuple[Handler, ...] = (_kill_switch, _quarantine, _conservative, _reject, _approve)


def run_chain(x: ChainInput) -> tuple[np.ndarray, np.ndarray]:
    """Decision and reason code per row; the first handler that claims a row decides it."""
    decision = np.full(len(x.scores), "", dtype=object)
    reason = np.full(len(x.scores), "", dtype=object)
    for handler in CHAIN:
        claim = handler(x)
        if claim is None:
            continue
        mask, value, code = claim
        free = mask & (decision == "")
        decision[free], reason[free] = value, code
    return decision, reason


def decisions_frame(keys: pd.Series, x: ChainInput) -> pd.DataFrame:
    """Final decisions with reason codes (pseudonymized keys only)."""
    decision, reason = run_chain(x)
    return pd.DataFrame({"loan_key": keys.to_numpy(), "score": x.scores, "decision": decision,
                         "reason_code": reason})  # fmt: skip
