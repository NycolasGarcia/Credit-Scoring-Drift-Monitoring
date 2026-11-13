"""Scenario simulator: config, determinism, S0 ~ reference, injected magnitude = configured."""

import json

import numpy as np
import pandas as pd
import pytest

from src.contracts.gate import GateOutcome
from src.contracts.schema import amortization_error
from src.data.features import model_feature_columns
from src.data.split import content_hash
from src.monitoring.profile import build_profile
from src.monitoring.psi import numeric_proportions, psi_from_proportions
from src.simulation.engine import SimContext, simulate, simulate_batch
from src.simulation.labels import relabel
from src.simulation.manifest import batch_summary, build_manifest, dumps
from src.simulation.natural import natural_labels
from src.simulation.record import build_record
from src.simulation.settings import ScenarioConfig, Schedule, load_scenario, scenario_ids
from src.simulation.transforms import drifted_features, intensity, secondary_features
from tests.synthetic import synthetic_batch

BASE_CFG = {"id": "S9", "name": "t", "drift_type": "none", "narrative": "t", "source": "holdout",
            "seed": 1, "label_lag": 2, "calendar_start": "2014-01", "batches": 4,
            "batch_size": 3000, "schedule": {"shape": "sudden", "onset": 1},
            "expected": {"layers": [], "diagnosis": "none"}}  # fmt: skip


def risk(df: pd.DataFrame) -> np.ndarray:
    """Known synthetic P(default | X), used both to draw labels and as the oracle."""
    z = -1.8 + 0.06 * (df["dti"] - 15) - 0.4 * np.log(df["annual_inc"] / 60000)
    return np.asarray(1 / (1 + np.exp(-z)), dtype=float)


@pytest.fixture(scope="module")
def base() -> pd.DataFrame:
    df = synthetic_batch(12000, seed=5)
    df["target"] = (np.random.default_rng(6).random(len(df)) < risk(df)).astype(float)
    return df


@pytest.fixture(scope="module")
def profile(base: pd.DataFrame) -> dict:
    return build_profile(base, pd.Series(risk(base)), {"threshold": 0.5})


def ctx(base, profile, **overrides) -> SimContext:
    return SimContext(ScenarioConfig.model_validate({**BASE_CFG, **overrides}), base, profile, risk)


def test_configured_scenarios_validate_and_cover_s0_to_s5() -> None:
    assert scenario_ids() == ["S0", "S1", "S2", "S3", "S4", "S5"]
    cfgs = {s: load_scenario(s) for s in scenario_ids()}
    s1 = {t.feature for t in cfgs["S1"].transforms}
    assert len(s1) >= 2 and s1 <= set(model_feature_columns())
    assert cfgs["S0"].transforms == [] and cfgs["S0"].schedule.shape == "none"
    assert len({c.seed for c in cfgs.values()}) == len(cfgs)


def test_intensity_shapes() -> None:
    grad = Schedule(shape="gradual", onset=2, ramp=4)
    assert [intensity(grad, t) for t in range(7)] == [0, 0, 0.25, 0.5, 0.75, 1, 1]
    rec = Schedule(shape="recurrent", onset=1, period=4)
    assert [intensity(rec, t) for t in range(6)] == [0, 1, 1, 0, 0, 1]
    assert intensity(Schedule(shape="none", onset=0), 5) == 0


def test_same_seed_same_hash_different_seed_differs(base, profile) -> None:
    def hashes(seed):
        return [content_hash(b.applications) + content_hash(b.labels)
                for b in simulate(ctx(base, profile, seed=seed))]  # fmt: skip

    assert hashes(1) == hashes(1)
    assert hashes(1) != hashes(2)


def test_s0_batches_are_indistinguishable_from_reference(base, profile) -> None:
    for batch in simulate(ctx(base, profile, schedule={"shape": "none"})):
        for col in ("annual_inc", "dti", "int_rate", "loan_amnt"):
            spec = profile["features"][col]
            props = numeric_proportions(batch.applications[col], spec["edges"])
            assert psi_from_proportions(spec["ref_props"], props) < 0.02
        assert abs(batch.labels["target"].mean() - base["target"].mean()) < 0.03


def test_injected_magnitude_equals_configured(base, profile) -> None:
    transforms = [{"kind": "scale", "feature": "annual_inc", "factor": 0.85},
                  {"kind": "shift", "feature": "int_rate", "delta": 3.0}]  # fmt: skip
    grad = {"shape": "gradual", "onset": 1, "ramp": 2}
    drifted = simulate_batch(ctx(base, profile, transforms=transforms, schedule=grad), 1)
    control = simulate_batch(ctx(base, profile, schedule=grad), 1)
    a, c = drifted.applications, control.applications
    assert drifted.level == 0.5
    assert np.allclose(a["annual_inc"] / c["annual_inc"], 1 + (0.85 - 1) * 0.5)
    assert np.allclose(a["int_rate"] - c["int_rate"], 1.5)
    assert amortization_error(a).max() < 1e-9


def test_covariate_shift_keeps_p_y_given_x(base, profile) -> None:
    transforms = [{"kind": "scale", "feature": "dti", "factor": 1.5}]
    labels = simulate_batch(ctx(base, profile, transforms=transforms, batch_size=10000), 2).labels
    assert abs(labels["target"].mean() - labels["p_oracle"].mean()) < 0.015
    assert labels["p_oracle"].mean() > base["target"].mean() + 0.02


def test_unit_bug_hits_configured_share_and_leaves_labels_untouched(base, profile) -> None:
    bug = [{"kind": "unit_bug", "feature": "annual_inc", "divisor": 12, "fraction": 0.3}]
    drifted = simulate_batch(ctx(base, profile, transforms=bug), 2)
    control = simulate_batch(ctx(base, profile), 2)
    ratio = drifted.applications["annual_inc"] / control.applications["annual_inc"]
    assert abs(np.isclose(ratio, 1 / 12).mean() - 0.3) < 0.03
    assert drifted.bug_rows == int(np.isclose(ratio, 1 / 12).sum())
    pd.testing.assert_frame_equal(drifted.labels, control.labels)


def test_logit_shift_moves_labels_only_in_segment(base, profile) -> None:
    shift = [{"kind": "logit_shift", "delta": 1.0,
              "segment": {"feature": "dti", "min_quantile": 0.7}}]  # fmt: skip
    drifted = simulate_batch(ctx(base, profile, transforms=shift, batch_size=10000), 2)
    control = simulate_batch(ctx(base, profile, batch_size=10000), 2)
    pd.testing.assert_frame_equal(drifted.applications, control.applications)
    seg = (drifted.applications["dti"] >= profile["features"]["dti"]["edges"][6]).to_numpy()
    y_d, y_c = drifted.labels["target"].to_numpy(), control.labels["target"].to_numpy()
    assert (y_d[~seg] == y_c[~seg]).all()
    assert y_d[seg].mean() > y_c[seg].mean() + 0.08
    assert abs(y_d[seg].mean() - drifted.labels["p_oracle"].to_numpy()[seg].mean()) < 0.03


def test_relabel_reaches_target_rate() -> None:
    rng = np.random.default_rng(0)
    p_old = rng.uniform(0.05, 0.4, 200_000)
    y = (rng.random(len(p_old)) < p_old).astype(int)
    for p_new in (p_old * 1.5, p_old * 0.5):
        assert abs(relabel(y, p_old, p_new, rng).mean() - p_new.mean()) < 0.003


def test_natural_labels_respect_maturity() -> None:
    rows = pd.DataFrame({"loan_key": ["a", "b", "c"], "term": [36, 60, 36],
                         "is_mature": [True, False, True],
                         "target": [1.0, 0.0, np.nan]})  # fmt: skip
    labels = natural_labels(rows, t=4)
    assert labels["target"].isna().tolist() == [False, True, True]
    assert labels["target"].iloc[0] == 1.0
    assert labels["label_batch"].tolist()[0] == 40 and labels["label_batch"].isna().sum() == 2


def test_manifest_is_strict_json_with_aggregates_only(base, profile) -> None:
    c = ctx(base, profile, transforms=[{"kind": "scale", "feature": "dti", "factor": 1.2}])
    batch = simulate_batch(c, 1)
    report = {"rows_quarantined": 0}
    outcome = GateOutcome("passed", pd.DataFrame(), report, None)
    manifest = build_manifest(c.cfg, "h", {"version": "v"}, [batch_summary(batch, outcome)])
    text = dumps(manifest)
    assert json.loads(text)["ground_truth"]["drifted_features"] == ["dti"]
    assert not any(k in text for k in batch.applications["loan_key"].head(100))


def test_run_record_groups_by_phase(base, profile) -> None:
    c = ctx(base, profile, transforms=[{"kind": "scale", "feature": "dti", "factor": 1.2}])
    outcome = GateOutcome("passed", pd.DataFrame(), {"rows_quarantined": 0}, None)
    rows = [batch_summary(b, outcome) for b in simulate(c)]
    manifest = build_manifest(c.cfg, "h", {"version": "v"}, rows)
    rec = build_record(c.cfg, manifest, ("sha", False))
    assert rec.kind == "sim" and set(rec.metrics) == {"pré-drift", "pós-onset"}
    assert rec.metrics["pré-drift"]["lotes"] == 1 and rec.metrics["pós-onset"]["lotes"] == 3


def test_ground_truth_separates_injected_and_secondary_features() -> None:
    s1 = load_scenario("S1").transforms
    assert drifted_features(s1) == ["annual_inc", "dti", "int_rate"]
    assert secondary_features(s1) == ["installment"]
    assert secondary_features(load_scenario("S4").transforms) == []
