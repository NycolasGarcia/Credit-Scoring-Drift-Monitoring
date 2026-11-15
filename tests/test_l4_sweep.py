"""L4 cut sweep: null-based choice rule, detection table and side effects."""

import numpy as np

from src.monitoring.l4_sweep import (
    choose_cut,
    detection_table,
    first_at,
    load_sweep_config,
    side_effects,
    variant,
)
from src.monitoring.settings import load_monitoring_config
from src.simulation.settings import load_scenario

TH = load_monitoring_config().get("bad_rate_ratio")
CFG = load_sweep_config()


def test_choice_rule_needs_zero_null_alarm_and_margin() -> None:
    null = np.full(100, 1.10)
    assert choose_cut(CFG, null) == min(c for c in CFG.cuts if c >= 1.10 + CFG.rule.min_margin)
    assert choose_cut(CFG, np.full(100, 1.49)) is None


def test_sweep_grid_stays_above_sev1() -> None:
    assert min(CFG.cuts) > TH.sev1


def test_first_at_uses_symmetric_ratio() -> None:
    series = {3: 1.0, 4: 1.0 / 1.4, 5: 1.3}
    assert first_at(series, 1.35, TH) == 4
    assert first_at(series, 1.45, TH) is None


def test_detection_table_counts_variants_and_delay() -> None:
    runs = [{"family": "S2 delta=1.0", "onset": 3, "series": {6: 1.1, 7: 1.3}},
            {"family": "S2 delta=1.0", "onset": 3, "series": {6: 1.0, 7: 1.1}}]  # fmt: skip
    row = next(r for r in detection_table(runs, [1.25], TH) if r["cut"] == 1.25)
    assert row["detected"] == 1 and row["variants"] == 2 and row["median_delay"] == 4


def test_side_effects_read_detector_evidence() -> None:
    ev = {
        "S9": {"batches": [{"index": 0, "l4": None}, {"index": 1, "l4": {"bad_rate_ratio": 1.4}}]}
    }
    rows = side_effects(ev, [1.3, 1.5], TH)
    assert [(r["cut"], r["batches_at_cut"]) for r in rows] == [(1.3, 1), (1.5, 0)]


def test_variant_changes_only_delta_and_seed() -> None:
    base = load_scenario("S2")
    v = variant(base, 1.5, 999)
    assert v.seed == 999 and v.transforms[0].delta == 1.5
    assert v.transforms[0].segment == base.transforms[0].segment and v.schedule == base.schedule
