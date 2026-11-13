"""Drift detection: PSI on known values, Evidently cross-check, severity, diagnosis, evaluation."""

import json
import math

import numpy as np
import pandas as pd
import pytest
from evidently import DataDefinition, Dataset, Report
from evidently.presets import DataDriftPreset
from scipy.stats import ks_2samp

from src.data.features import model_feature_columns
from src.monitoring.calibration import bin_codes, calibrate_signal, psi_codes
from src.monitoring.detect import Batch, DetectContext, detect_batch
from src.monitoring.diagnosis import diagnose, unit_bug_signature
from src.monitoring.drift import drift_table, feature_psi, wasserstein_norm
from src.monitoring.evaluation import evaluate
from src.monitoring.evidently_report import build_report, column_values
from src.monitoring.performance import observable_at, segment_gap
from src.monitoring.profile import build_profile
from src.monitoring.psi import categorical_proportions, psi_from_proportions
from src.monitoring.settings import load_monitoring_config
from src.monitoring.severity import batch_severity, feature_level, level
from tests.synthetic import synthetic_batch

CFG = load_monitoring_config()


@pytest.fixture(scope="module")
def reference() -> pd.DataFrame:
    return synthetic_batch(8000, seed=21)


@pytest.fixture(scope="module")
def profile(reference: pd.DataFrame) -> dict:
    summary = {"threshold": 0.5, "approval_rate": 0.9,
               "importance_rank": ["annual_inc", "dti", "int_rate", *model_feature_columns()[5:]],
               "reference_metrics": {"auc": 0.70}}  # fmt: skip
    return build_profile(reference, pd.Series(np.random.default_rng(3).random(8000)), summary)


def test_psi_of_identical_distribution_is_zero(reference, profile) -> None:
    assert max(feature_psi(reference[f], s) for f, s in profile["features"].items()) < 1e-12


def test_psi_of_known_shift_matches_closed_form() -> None:
    ref = categorical_proportions(pd.Series(["a"] * 50 + ["b"] * 50), ["a", "b"])
    cur = categorical_proportions(pd.Series(["a"] * 70 + ["b"] * 30), ["a", "b"])
    expected = 0.2 * math.log(0.7 / 0.5) + (-0.2) * math.log(0.3 / 0.5)
    assert psi_from_proportions(ref, cur) == pytest.approx(expected, abs=1e-9)


def test_vectorized_psi_equals_reference_implementation(reference, profile) -> None:
    batch = synthetic_batch(3000, seed=4).assign(dti=lambda d: d["dti"] * 1.3)
    batch.loc[::7, "mths_since_last_delinq"] = np.nan
    for f, spec in profile["features"].items():
        ref_vec = np.array(list(spec["ref_props"].values()))
        assert psi_codes(bin_codes(batch[f], spec), ref_vec) == pytest.approx(
            feature_psi(batch[f], spec), abs=1e-12)  # fmt: skip


def test_evidently_psi_ref_equals_own_psi(reference, profile) -> None:
    cur = synthetic_batch(3000, seed=5).assign(annual_inc=lambda d: d["annual_inc"] * 0.8)
    snap = build_report(reference, cur, ["annual_inc", "dti"], ["grade"], 0.1)
    values = column_values(snap)
    for col in ("annual_inc", "dti", "grade"):
        assert values[col] == pytest.approx(feature_psi(cur[col], profile["features"][col]), 1e-9)


def test_evidently_builtin_ks_and_wasserstein_match_scipy(reference) -> None:
    cur = synthetic_batch(3000, seed=6).assign(dti=lambda d: d["dti"] + 2)
    dd = DataDefinition(numerical_columns=["dti", "annual_inc"])
    preset = DataDriftPreset(per_column_method={"dti": "ks", "annual_inc": "wasserstein"})
    snap = Report([preset]).run(Dataset.from_pandas(cur[["dti", "annual_inc"]], data_definition=dd),
                                Dataset.from_pandas(reference[["dti", "annual_inc"]],
                                                    data_definition=dd))  # fmt: skip
    values = column_values(snap)
    assert values["dti"] == pytest.approx(ks_2samp(reference["dti"], cur["dti"])[1], rel=1e-9)
    assert values["annual_inc"] == pytest.approx(
        wasserstein_norm(reference["annual_inc"], cur["annual_inc"]), rel=1e-9)  # fmt: skip


def test_severity_respects_direction() -> None:
    assert level(-4.0, CFG.get("approval_delta_pp")) == level(4.0, CFG.get("approval_delta_pp"))
    ratio = CFG.get("bad_rate_ratio")
    assert level(1 / 1.3, ratio) == level(1.3, ratio) >= 1
    assert level(-0.2, CFG.get("auc_drop")) == 0
    assert level(None, ratio) == 0


def test_feature_level_rules() -> None:
    th = CFG.get("feature_psi")
    table = pd.DataFrame({"feature": list("abcde"), "importance_rank": [1, 2, 3, 40, 41],
                          "psi": [0.0, 0.0, 0.0, th.sev2 + 0.1, 0.0]})  # fmt: skip
    assert feature_level(table, th, top_k=10)[0] == 1
    table.loc[0, "psi"] = th.sev2
    assert feature_level(table, th, top_k=10)[0] == 2
    table.loc[[1, 2], "psi"] = th.sev2
    assert feature_level(table, th, top_k=10) == (3, ["a", "b", "c", "d"])


def test_unit_bug_signature_finds_monthly_income_not_inflation(reference, profile) -> None:
    spec, cur = profile["features"]["annual_inc"], synthetic_batch(4000, seed=8)
    bugged = cur["annual_inc"].where(np.arange(len(cur)) % 10 >= 3, cur["annual_inc"] / 12)
    sig = unit_bug_signature(reference["annual_inc"], bugged, spec, CFG.diagnosis)
    assert sig is not None and sig["factor"] == 12
    assert unit_bug_signature(reference["annual_inc"], cur["annual_inc"] * 0.85, spec,
                              CFG.diagnosis) is None  # fmt: skip


@pytest.mark.parametrize(("gate", "signals", "l4", "bugs", "expected"), [
    ("blocked", {}, None, {}, "D0"),
    ("passed", {"feature_psi": 2}, None, {"annual_inc": {}}, "D6"),
    ("passed", {"auc_drop": 1, "bad_rate_ratio": 0}, {"segment_gap": 0.0}, {}, "D3"),
    ("passed", {"auc_drop": 0, "bad_rate_ratio": 1}, {"segment_gap": 2.0}, {}, "D3"),
    ("passed", {"auc_drop": 0, "bad_rate_ratio": 1}, {"segment_gap": 0.1}, {}, "D2"),
    ("passed", {"feature_psi": 1}, None, {}, "D1"),
    ("passed", {"score_psi": 1}, None, {}, "D4"),
    ("passed", {}, None, {}, "none"),
])  # fmt: skip
def test_diagnosis_follows_decision_tree(gate, signals, l4, bugs, expected) -> None:
    base = dict.fromkeys(("feature_psi", "score_psi", "approval_delta_pp", "bad_rate_ratio",
                          "auc_drop"), 0)  # fmt: skip
    assert diagnose(gate, {"signals": {**base, **signals}}, l4, bugs, CFG) == expected


def test_segment_gap_finds_the_shifted_segment(profile) -> None:
    rng = np.random.default_rng(9)
    frame = synthetic_batch(20000, seed=10).assign(score=0.15)
    high = frame["dti"] >= profile["features"]["dti"]["edges"][7]
    frame["target"] = (rng.random(len(frame)) < np.where(high, 0.35, 0.15)).astype(int)
    gap, feature = segment_gap(frame, profile, top_k=3)
    assert feature == "dti" and gap > 0.8


def test_observable_at_respects_label_lag() -> None:
    hist = pd.DataFrame({"label_batch": [3, 3, 4, 5], "target": [1.0, np.nan, 0.0, 1.0]})
    assert observable_at(hist, 3).index.tolist() == [0]


def test_drift_table_flags_shifted_features(reference, profile) -> None:
    cur = synthetic_batch(4000, seed=12).assign(dti=lambda d: d["dti"] * 1.6)
    table = drift_table(reference, cur, profile)
    assert table.iloc[0]["feature"] == "dti" and table.iloc[0]["psi"] >= CFG.get("feature_psi").sev1
    sev = batch_severity(table, {"score_psi": 0.0, "approval_delta_pp": 0.0}, None, CFG)
    assert sev["level"] >= 1 and sev["flagged_features"] == ["dti"]


def test_evaluate_measures_delay_attribution_and_diagnosis() -> None:
    def res(i, lvl, diag, feats):
        sig = dict.fromkeys(("feature_psi", "score_psi", "approval_delta_pp", "bad_rate_ratio",
                             "auc_drop"), 0) | {"feature_psi": lvl}  # fmt: skip
        return {"index": i, "diagnosis": diag,
                "severity": {"level": lvl, "signals": sig, "flagged_features": feats}}  # fmt: skip

    results = [res(0, 0, "none", []), res(1, 1, "D1", ["x"]), res(2, 0, "none", []),
               res(3, 2, "D1", ["dti", "x"]), res(4, 2, "D4", ["dti"])]  # fmt: skip
    gt = {"onset_batch": 2, "drift_type": "D1", "drifted_features": ["dti", "int_rate"],
          "expected_layers": ["L2"], "expected_diagnosis": "D1"}  # fmt: skip
    ev = evaluate(results, gt)
    assert ev["false_alarm"]["sev1_plus"] == 0.5 and ev["delay_sev1"] == 1
    assert ev["attribution"]["recall"] == 0.5 and ev["attribution"]["precision"] == 0.5
    assert ev["diagnosis"]["accuracy"] == 0.5 and ev["layers_fired"] == ["L2"]


def test_calibration_keeps_proposal_as_floor_and_clears_null_max() -> None:
    null = pd.DataFrame({"auc_drop": np.linspace(0, 0.03, 500)})
    out = calibrate_signal(null, "auc_drop", CFG)
    th = CFG.get("auc_drop")
    assert out["sev1"] >= th.sev1 and out["sev2"] > null["auc_drop"].max()
    assert out["fa_proposed_sev1"] == pytest.approx((null["auc_drop"] >= th.sev1).mean())


def test_batch_result_is_strict_json(reference, profile) -> None:
    apps = synthetic_batch(1500, seed=13)
    scored = pd.DataFrame({"loan_key": apps["loan_key"], "score": 0.2, "decision": "approve"})
    labels = pd.DataFrame({"loan_key": apps["loan_key"], "target": np.nan, "label_batch": 9})
    hist = scored.merge(labels, on="loan_key").assign(cohort=0)
    batch = Batch(0, "b", "2014-01", "passed", apps, scored, labels)
    out = detect_batch(DetectContext(reference, profile, CFG), batch, hist)
    json.dumps(out, allow_nan=False)


def test_evaluation_without_ground_truth_reports_undefined_metrics() -> None:
    sig = dict.fromkeys(("feature_psi", "score_psi", "approval_delta_pp", "bad_rate_ratio",
                         "auc_drop"), 0) | {"feature_psi": 1}  # fmt: skip
    results = [{"index": 0, "diagnosis": "D1",
                "severity": {"level": 1, "signals": sig, "flagged_features": ["x"]}}]  # fmt: skip
    gt = {"onset_batch": None, "drift_type": "natural", "drifted_features": [],
          "expected_layers": [], "expected_diagnosis": "unknown"}  # fmt: skip
    ev = evaluate(results, gt)
    assert ev["attribution"]["precision"] is None and ev["diagnosis"]["accuracy"] is None
