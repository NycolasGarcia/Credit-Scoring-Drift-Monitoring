"""Data contract: each rule fails in isolation, the gate blocks and never scores bad batches."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.contracts.d6 import sweep
from src.contracts.gate import EXIT_BLOCKED, EXIT_OK, GateContext, run_gate
from src.contracts.rules import RULES
from src.contracts.schema import application_columns
from src.contracts.settings import load_contract_config
from src.contracts.validate import validate_input, validate_output
from src.data.features import CATEGORICAL_FEATURES, model_feature_columns
from src.monitoring.profile import build_profile
from src.simulation.bad_batch import DEFECTS, make_bad_batch

CFG = load_contract_config()
BELOW_TOLERANCE = CFG.batch.max_row_failure_rate / 2
COLLATERAL = {"wrong_type": {"H05", "H08"}}  # a text column also breaks checks that read it
LEVELS = {"grade": list("ABCDEFG"), "home_ownership": ["MORTGAGE", "OWN", "RENT"],
          "verification_status": ["Not Verified", "Source Verified", "Verified"],
          "purpose": ["credit_card", "debt_consolidation", "other"]}  # fmt: skip


def synthetic_batch(n: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Valid application batch with the real schema and plausible values."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.uniform(1, 30, n) for c in model_feature_columns()})
    df["loan_amnt"] = rng.uniform(1000, 35000, n).round(0)
    df["term"] = rng.choice([36, 60], n).astype("int64")
    df["int_rate"] = rng.uniform(6, 25, n)
    r = df["int_rate"] / 1200
    df["installment"] = df["loan_amnt"] * r / (1 - (1 + r) ** (-df["term"]))
    df["annual_inc"] = rng.lognormal(11, 0.5, n)
    df["fico_range_low"] = rng.integers(660, 800, n).astype(float)
    df["emp_length"] = rng.integers(0, 11, n).astype(float)
    for col, levels in LEVELS.items():
        df[col] = rng.choice(levels, n)
    df["loan_key"] = [f"k{i:06d}" for i in range(n)]
    df["issue_d"] = pd.Timestamp("2013-06-01")
    df["addr_state"] = rng.choice(["CA", "NY", "TX"], n)
    return df[application_columns()]


@pytest.fixture(scope="module")
def profile() -> dict:
    ref = synthetic_batch(5000, seed=1)
    return build_profile(ref, pd.Series(np.random.default_rng(2).random(5000)), {"threshold": 0.5})


def test_valid_batch_passes(profile: dict) -> None:
    result = validate_input(synthetic_batch(), profile, CFG)
    assert result.status == "passed" and result.rule_counts == {}
    assert len(result.valid) == result.rows_in


def test_contract_has_at_least_eight_hard_input_rules() -> None:
    hard = [r for r in RULES.values() if r.severity == "hard" and r.id.startswith("H")]
    assert len(hard) >= 8


def test_every_hard_input_rule_has_an_isolating_defect() -> None:
    covered = {d.expected_rule for d in DEFECTS.values()}
    hard = {r.id for r in RULES.values() if r.severity == "hard" and r.id.startswith("H")}
    assert hard <= covered


@pytest.mark.parametrize("name", sorted(DEFECTS))
def test_each_defect_trips_its_rule_in_isolation(name: str, profile: dict) -> None:
    batch, _ = make_bad_batch(synthetic_batch(), [name], seed=3, rate=BELOW_TOLERANCE)
    result = validate_input(batch, profile, CFG)
    expected = DEFECTS[name].expected_rule
    if RULES[expected].severity == "soft":
        assert result.soft[expected]["triggered"] and result.rule_counts == {}
        return
    assert expected in result.rule_counts
    assert set(result.rule_counts) <= {expected} | COLLATERAL.get(name, set())
    blocking = RULES[expected].scope in {"schema", "batch"}
    assert result.status == ("blocked" if blocking else "partial")


def test_too_many_bad_rows_block_the_batch(profile: dict) -> None:
    batch, _ = make_bad_batch(synthetic_batch(), ["negative_income"], seed=3, rate=0.05)
    assert validate_input(batch, profile, CFG).status == "blocked"


class CountingModel:
    """Fake model that records whether it was asked to score."""

    def __init__(self) -> None:
        self.calls = 0

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        self.calls += 1
        return np.column_stack([np.full(len(x), 0.9), np.full(len(x), 0.1)])


def test_gate_never_scores_a_blocked_batch(profile: dict, tmp_path: Path) -> None:
    batch, _ = make_bad_batch(synthetic_batch(), ["monthly_income"], seed=3, rate=0.01)
    model = CountingModel()
    out = run_gate(batch, "b1", GateContext(model, 0.5, "v1", profile, CFG, tmp_path))
    assert out.status == "blocked" and model.calls == 0 and out.scored.empty
    assert out.exit_code == EXIT_BLOCKED
    assert (tmp_path / "b1" / "report.json").exists()


def test_gate_scores_only_valid_rows_of_a_partial_batch(profile: dict, tmp_path: Path) -> None:
    batch, _ = make_bad_batch(synthetic_batch(), ["sentinel"], seed=3, rate=BELOW_TOLERANCE)
    out = run_gate(batch, "b2", GateContext(CountingModel(), 0.5, "v1", profile, CFG, tmp_path))
    assert out.status == "partial" and out.exit_code == EXIT_OK
    assert (
        len(out.scored) == out.report["rows_valid"] == len(batch) - out.report["rows_quarantined"]
    )
    assert set(out.scored["decision"]) == {"approve"}


def test_quarantine_report_has_no_row_values(profile: dict, tmp_path: Path) -> None:
    batch, _ = make_bad_batch(synthetic_batch(), list(DEFECTS), seed=3, rate=0.01)
    run_gate(batch, "b3", GateContext(CountingModel(), 0.5, "v1", profile, CFG, tmp_path))
    text = (tmp_path / "b3" / "report.json").read_text(encoding="utf-8")
    report = json.loads(text)
    assert report["status"] == "blocked"
    assert not any(k in text for k in batch["loan_key"].head(200))
    assert not any(f"{v:.2f}" in text for v in batch["annual_inc"].dropna().head(200))


def test_output_contract_catches_bad_scores_and_inconsistent_decisions() -> None:
    scored = pd.DataFrame({"loan_key": ["a", "b"], "score": [0.2, 0.7],
                           "decision": ["approve", "reject"], "model_version": "v"})  # fmt: skip
    assert validate_output(scored, CFG, 0.5) == {}
    assert "O02" in validate_output(scored.assign(score=[1.5, 0.7]), CFG, 0.5)
    assert "O03" in validate_output(scored.assign(decision=["reject", "reject"]), CFG, 0.5)


def test_d6_sweep_contract_catches_full_unit_bug(profile: dict) -> None:
    rows = sweep(synthetic_batch(), profile, CFG, seed=0)
    full = next(r for r in rows if r["fraction_monthly"] == 1.0)
    small = next(r for r in rows if r["fraction_monthly"] == 0.1)
    assert full["h10_triggered"] and full["contract_status"] == "blocked"
    assert not small["h10_triggered"] and small["annual_inc_psi"] > 0


def test_categorical_features_are_strings_in_schema() -> None:
    assert set(CATEGORICAL_FEATURES) <= set(application_columns())
