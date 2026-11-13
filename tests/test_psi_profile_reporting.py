"""PSI against known values, reference profile structure and RUN record rendering."""

import numpy as np
import pandas as pd
import pytest

from src.data.features import model_feature_columns
from src.monitoring.profile import build_profile
from src.monitoring.psi import (
    EPS,
    NULL_BIN,
    OTHER_BIN,
    categorical_proportions,
    numeric_proportions,
    psi_from_proportions,
    psi_numeric,
    quantile_edges,
)
from src.reporting import run_record as rr
from src.reporting.run_record import RunRecord, render


def test_psi_identical_distribution_is_zero() -> None:
    s = pd.Series(np.random.default_rng(0).normal(size=5000))
    assert psi_numeric(s, s) == pytest.approx(0.0, abs=1e-12)


def test_psi_matches_hand_computed_value() -> None:
    ref, cur = {"a": 0.5, "b": 0.5}, {"a": 0.25, "b": 0.75}
    expected = (0.25 - 0.5) * np.log(0.25 / 0.5) + (0.75 - 0.5) * np.log(0.75 / 0.5)
    assert psi_from_proportions(ref, cur) == pytest.approx(expected)


def test_psi_grows_with_shift() -> None:
    rng = np.random.default_rng(1)
    ref = pd.Series(rng.normal(size=20000))
    small, large = psi_numeric(ref, ref + 0.1), psi_numeric(ref, ref + 1.0)
    assert 0 < small < 0.1
    assert large > 0.25


def test_bins_are_fixed_by_reference_and_nulls_have_their_own_bin() -> None:
    ref = pd.Series([1.0, 2.0, 3.0, 4.0, np.nan])
    edges = quantile_edges(ref, n_bins=2)
    props = numeric_proportions(pd.Series([10.0, np.nan]), edges)
    assert edges == [2.5]
    assert props[NULL_BIN] == 0.5 and props["b1"] == 0.5


def test_unseen_category_goes_to_other_bin() -> None:
    props = categorical_proportions(pd.Series(["A", "Z", None]), ["A", "B"])
    assert props == pytest.approx({"A": 1 / 3, "B": 0.0, OTHER_BIN: 1 / 3, NULL_BIN: 1 / 3})


def test_empty_bin_uses_epsilon_not_infinity() -> None:
    assert np.isfinite(psi_from_proportions({"a": 1.0, "b": 0.0}, {"a": 0.0, "b": 1.0}))
    assert EPS > 0


def test_profile_covers_every_model_feature() -> None:
    rng = np.random.default_rng(2)
    ref = pd.DataFrame({c: rng.normal(size=200) for c in model_feature_columns()})
    for c in ("grade", "home_ownership", "verification_status", "purpose"):
        ref[c] = rng.choice(["X", "Y"], 200)
    profile = build_profile(ref, pd.Series(rng.random(200)), {"threshold": 0.3})
    assert set(profile["features"]) == set(model_feature_columns())
    assert profile["features"]["grade"]["type"] == "categorical"
    assert len(profile["score"]["edges"]) == 9


def test_run_record_marks_dirty_tree_and_renders_metrics() -> None:
    rec = RunRecord(run_id="RUN-X", kind="train", scenario="REF", seed=1, data_hash="h",
                    model="m", mlflow_ref="r", metrics={"test": {"auc": 0.7}}, verdict="ok",
                    dirty=True)  # fmt: skip
    text = render(rec)
    assert "NÃO REPRODUTÍVEL" in text
    assert "| auc | 0.7000 |" in text


def test_write_record_keeps_git_state_captured_at_job_start(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(rr, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(rr, "INDEX", tmp_path / "INDEX.md")
    monkeypatch.setattr(rr, "git_state", lambda: ("later-sha", True))
    for i in (1, 2):
        rr.write_record(RunRecord(run_id=f"RUN-{i}", kind="train", scenario="REF", seed=1,
                                  data_hash="h", model="m", mlflow_ref="r", metrics={},
                                  verdict="ok", sha="start-sha", dirty=False))  # fmt: skip
    index = (tmp_path / "INDEX.md").read_text(encoding="utf-8")
    assert index.count("| sim |") == 2
    assert "later-sha" not in (tmp_path / "RUN-2.md").read_text(encoding="utf-8")
