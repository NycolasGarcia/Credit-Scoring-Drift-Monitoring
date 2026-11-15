"""Response: policy matrix, circuit breaker, guardrail chain with reason codes, respond step."""

import numpy as np
import pandas as pd
import pytest

from src.response import respond as respond_mod
from src.response.guardrails import (
    BreakerState,
    ChainInput,
    negative_value,
    risk_correction,
    run_chain,
)
from src.response.policy import PolicyFacts, decide, output_level
from src.response.respond import ResponseMemory, respond
from src.response.settings import load_policy
from tests.synthetic import synthetic_batch

POLICY = load_policy()
SCORES = np.array([0.05, 0.20, 0.35, 0.45, 0.60])


@pytest.mark.parametrize(("diagnosis", "out", "batch", "rule", "conservative"), [
    ("D0", 0, 2, "P01", False), ("D6", 2, 2, "P02", False), ("D3", 2, 2, "P03", True),
    ("D3", 1, 1, "P04", False), ("D2", 2, 2, "P05", True), ("D2", 1, 1, "P06", False),
    ("D4", 2, 2, "P07", True), ("D1", 1, 2, "P09", False), ("none", 0, 3, "P08", False),
    ("none", 0, 0, "P00", False),
])  # fmt: skip
def test_policy_matrix_rows(diagnosis, out, batch, rule, conservative) -> None:
    decision = decide(PolicyFacts(diagnosis, batch, out), POLICY)
    assert decision.rule_id == rule and decision.wants_conservative == conservative


def test_only_output_alerts_count_for_the_policy() -> None:
    assert output_level({"CDM_FEATURE_DRIFT": 3, "CDM_SCORE_DRIFT": 1}, POLICY) == 1


def test_every_rule_action_is_in_the_catalog() -> None:
    codes = {a.code for r in POLICY.rules for a in r.actions}
    assert (
        codes <= set(POLICY.actions) and POLICY.rules[-1].when.model_dump(exclude_none=True) == {}
    )


def test_breaker_opens_and_closes_after_cool_down() -> None:
    b = BreakerState()
    b.update(True, POLICY, 4)
    assert b.open and b.opened_at == 4
    for t in range(5, 5 + POLICY.cool_down_batches):
        b.update(False, POLICY, t)
    assert not b.open


def test_human_override_wins_over_the_breaker() -> None:
    b = BreakerState()
    b.update(True, POLICY.model_copy(update={"conservative_mode": "off"}), 1)
    assert not b.open


def test_negative_value_grows_with_the_risk_correction() -> None:
    p = np.array([0.10, 0.30, 0.45])
    gain, loss = np.array([1000.0, 1000.0, 1000.0]), np.array([3000.0, 3000.0, 3000.0])
    assert list(negative_value(p, gain, loss, 1.0)) == [False, True, True]
    assert risk_correction(1.4, POLICY.conservative) == 1.4
    assert risk_correction(0.8, POLICY.conservative) == 1.0
    assert risk_correction(None, POLICY.conservative) == 1.0


def chain(**kw) -> ChainInput:
    base = {"scores": SCORES, "base_threshold": 0.495,
            "negative_value": np.array([False, False, True, True, True]),
            "kill_switch": False, "quarantine": False, "conservative": False}  # fmt: skip
    return ChainInput(**{**base, **kw})


def test_chain_base_threshold_decides_with_reason_codes() -> None:
    decision, reason = run_chain(chain())
    assert list(decision) == ["approve"] * 4 + ["reject"] and list(reason) == ["R00"] * 4 + ["R01"]


def test_conservative_mode_sends_the_gray_zone_to_review() -> None:
    decision, reason = run_chain(chain(conservative=True))
    assert list(decision) == ["approve", "approve", "review", "review", "reject"]
    assert list(reason) == ["R00", "R00", "R10", "R10", "R01"]


@pytest.mark.parametrize(("flag", "code"), [("kill_switch", "R20"), ("quarantine", "R30")])
def test_kill_switch_and_quarantine_hold_every_decision(flag: str, code: str) -> None:
    decision, reason = run_chain(chain(conservative=True, **{flag: True}))
    assert set(decision) == {"review"} and set(reason) == {code}


def scored() -> pd.DataFrame:
    """Validated rows with the fields the economics need, plus the champion score."""
    return synthetic_batch(5, seed=3).assign(score=SCORES)


def signals(diagnosis: str = "D3", level: int = 2) -> dict:
    return {"diagnosis": diagnosis, "batch_level": level, "bad_rate_ratio": None,
            "levels": {"CDM_BAD_RATE_RATIO": level}}  # fmt: skip


def test_respond_opens_conservative_mode_on_confirmed_degradation() -> None:
    frame, summary = respond(8, scored(), signals(), ResponseMemory(), 0.495)
    assert summary["rule"] == "P03" and summary["conservative"]
    assert summary["auto"] == ["A4", "A6"] and set(frame["reason_code"]) <= {"R00", "R01", "R10"}
    assert (
        summary["expected_bad_rate_approved"] is None or summary["expected_bad_rate_approved"] < 1
    )


@pytest.mark.parametrize("override", [{"kill_switch": True}, {"dry_run": True}])
def test_kill_switch_and_dry_run_read_from_policy(monkeypatch, override: dict) -> None:
    monkeypatch.setattr(respond_mod, "load_policy", lambda: POLICY.model_copy(update=override))
    frame, summary = respond(8, scored(), signals(), ResponseMemory(), 0.495)
    if "kill_switch" in override:
        assert set(frame["reason_code"]) == {"R20"}
    else:
        assert set(frame["decision"]) <= {"approve", "reject"} and summary["conservative"]


def test_quarantine_holds_a_suspected_bug_batch() -> None:
    frame, summary = respond(5, scored(), signals("D6"), ResponseMemory(), 0.495)
    assert summary["rule"] == "P02" and set(frame["reason_code"]) == {"R30"}
