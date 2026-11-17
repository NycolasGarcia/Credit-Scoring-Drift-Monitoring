"""Robustness study: magnitude scaling of variants, Wilson interval and the declared reading."""

import pytest

from src.monitoring.robustness import (
    detection_row,
    load_robustness,
    response_summary,
    summarize_cell,
    variant,
    verdict,
    wilson,
)
from src.simulation.settings import load_scenario

CFG = load_robustness()


@pytest.mark.parametrize("m", [0.25, 1.0, 1.5])
def test_variant_scales_every_transform_and_changes_only_seed_and_magnitude(m: float) -> None:
    s1, s4 = load_scenario("S1"), load_scenario("S4")
    v1, v4 = variant(s1, m, 999), variant(s4, m, 999)
    factors = {t.feature: t for t in v1.transforms}
    assert factors["annual_inc"].factor == pytest.approx(1 + (0.85 - 1) * m)
    assert factors["int_rate"].delta == pytest.approx(3.0 * m)
    assert v4.transforms[0].fraction == pytest.approx(0.30 * m)
    assert v1.seed == 999 and v1.schedule == s1.schedule and v1.batches == s1.batches


def test_official_magnitude_reproduces_the_official_transforms() -> None:
    for sid in ("S1", "S2", "S3", "S4"):
        base = load_scenario(sid)
        assert variant(base, 1.0, base.seed) == base


def test_wilson_interval() -> None:
    lo, hi = wilson(20, 20)
    assert hi == 1.0 and 0.83 < lo < 0.84
    assert wilson(0, 0) is None


def _row(first2, correct, alerting, pre_sev2=0):
    return {"first_sev1": first2, "first_sev2": first2, "onset": 3, "correct": correct,
            "alerting": alerting, "pre_batches": 3, "pre_sev1": pre_sev2,
            "pre_sev2": pre_sev2}  # fmt: skip


def test_declared_reading_rule() -> None:
    good = summarize_cell([_row(8, 4, 4) for _ in range(5)], 2)
    assert verdict(good, CFG.reading) == {"detection": True, "diagnosis": True,
                                          "false_alarm": True}  # fmt: skip
    missed = summarize_cell([_row(None, 0, 0)] * 2 + [_row(8, 4, 4)] * 3, 2)
    assert verdict(missed, CFG.reading)["detection"] is False  # 3/5 < 80%
    control = summarize_cell([_row(None, 0, 0)] * 5, 2)
    assert verdict(control, CFG.reading, control=True)["detection"] is None
    noisy = summarize_cell([_row(8, 4, 4, pre_sev2=1)] + [_row(8, 4, 4)] * 4, 2)
    assert verdict(noisy, CFG.reading)["false_alarm"] is False


def test_response_summary_requires_gain_in_every_seed() -> None:
    rows = [{"scenario": "S2", "deltas": {"a": d, "b": 1.0}} for d in (5.0, -1.0, 3.0)]
    by = {r["strategy"]: r for r in response_summary(rows, CFG.reading)}
    assert by["a"]["positive"] == 2 and not by["a"]["robust"] and by["a"]["median"] == 3.0
    assert by["b"]["robust"]


def test_contract_blocked_batches_are_counted_apart_from_the_detector() -> None:
    def res(i, level, diag, gate="passed"):
        sev = {"level": level}
        return {"index": i, "severity": sev, "gate_status": gate, "diagnosis": diag}

    results = [res(0, 0, "none"), res(1, 2, "D6"), res(2, 2, "D0", "blocked")]
    ev = {"onset": 1, "first_sev1": 1, "first_sev2": 1, "attribution": {"recall": 1.0},
          "diagnosis": {"expected": "D6", "counts": {"D6": 1, "D0": 1}}}  # fmt: skip
    row = detection_row("S4", 1.5, 304, results, ev)
    assert row["blocked"] == 1 and row["alerting"] == 1 and row["correct"] == 1
