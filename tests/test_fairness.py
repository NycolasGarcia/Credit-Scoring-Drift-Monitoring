"""Bias analysis and mitigation: group metrics, fairness drift and the conservative-mode cap."""

import numpy as np
import pandas as pd

from src.governance.fairness import (
    approval_gap,
    cramers_v,
    fairness_drift,
    gaps,
    groups,
    load_fairness,
    segment_table,
)
from src.response.fairness_cap import relief
from src.response.settings import FairnessCap

CFG = load_fairness()
CAP = FairnessCap(segment="g", max_gap_pp=10.0, min_group_rows=2)


def test_emp_length_bands_and_unknown() -> None:
    frame = pd.DataFrame({"emp_length": [0.0, 1.0, 4.0, 5.0, 10.0, np.nan]})
    labels = groups(frame, "emp_length", CFG.segments["emp_length"]).tolist()
    assert labels == ["0-1", "1-5", "1-5", "5-10", "10+", "desconhecido"]


def test_segment_table_and_gaps() -> None:
    frame = pd.DataFrame({"g": ["a"] * 4 + ["b"] * 4, "target": [0, 0, 1, 0, 0, 1, 1, 0],
                          "score": [0.1, 0.2, 0.6, 0.1, 0.2, 0.5, 0.6, 0.1]})  # fmt: skip
    approved = frame["score"].to_numpy() < 0.4
    table = segment_table(frame, approved, "g", CFG.segments["home_ownership"])
    assert table["a"]["approval_rate"] == 0.75 and table["b"]["approval_rate"] == 0.5
    assert table["a"]["good_approval_rate"] == 1.0
    assert gaps(table, 4)["approval_rate"] == 0.25
    assert gaps(table, 5)["approval_rate"] is None  # groups too small to compare


def test_relief_closes_the_gap_with_the_best_held_values() -> None:
    labels = np.array(["a"] * 10 + ["b"] * 10)
    approved = np.array([True] * 10 + [True] * 5 + [False] * 5)  # gap of 50 p.p.
    held = ~approved
    value = np.array([0.0] * 10 + [0.0] * 5 + [-1, -5, -2, -9, -3], float)
    back = relief(approved, held, value, labels, CAP)
    assert back.sum() == 4  # 50% -> 90%, within 10 p.p. of the best group
    assert not back[18]  # the worst expected value (-9) stays held
    after = approved | back
    assert approval_gap(after, labels, 2) <= 0.10 + 1e-9


def test_relief_never_touches_rows_that_were_not_held() -> None:
    labels = np.array(["a"] * 4 + ["b"] * 4)
    approved = np.array([True] * 4 + [False] * 4)
    held = np.zeros(8, bool)  # rejected by the champion itself, not by the conservative mode
    assert not relief(approved, held, np.zeros(8), labels, CAP).any()


def test_fairness_drift_compares_policy_with_the_plain_champion() -> None:
    frame = pd.DataFrame({"home_ownership": ["RENT"] * 300 + ["OWN"] * 300,
                          "emp_length": [5.0] * 600, "addr_state": ["CA"] * 600})  # fmt: skip
    champion = np.ones(600, bool)
    policy = np.array([True] * 240 + [False] * 60 + [True] * 300)  # RENT 80%, OWN 100%
    out = fairness_drift(frame, policy, champion, CFG)
    assert round(out["segments"]["home_ownership"]["increase_pp"], 6) == 20.0
    assert out["level"] == 2


def test_cramers_v_bounds() -> None:
    a = pd.Series(list("xxyy") * 10)
    assert cramers_v(a, a) == 1.0
    assert cramers_v(a, pd.Series(list("xyxy") * 10)) < 0.1
