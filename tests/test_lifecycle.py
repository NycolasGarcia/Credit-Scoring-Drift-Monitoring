"""Lifecycle: GR-7/GR-8 refusals, recalibration, promotion gate, promote/rollback, comparison."""

from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression

from src.data.features import model_feature_columns
from src.models.settings import load_cost_config
from src.response import compare as cmp
from src.response.gate import evaluate_gate
from src.response.lifecycle import (
    BatchView,
    TrainingRefusedError,
    challenger_rows,
    fit_recalibration,
    load_lifecycle,
    recalibration_rows,
)
from src.response.registry_ops import alias_version, promote, rollback
from src.response.settings import load_policy
from tests.synthetic import synthetic_batch

CFG = load_lifecycle()
NUMERIC = ["dti", "annual_inc", "int_rate"]


def risk(df: pd.DataFrame) -> np.ndarray:
    z = -2.0 + 0.08 * (df["dti"] - 15) + 0.10 * (df["int_rate"] - 15)
    return 1 / (1 + np.exp(-z))


class Linear:
    """Small fitted model with the predict_proba contract of the champion."""

    def __init__(self, est) -> None:
        self.est = est

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        return self.est.predict_proba(x[NUMERIC])


def fit(df: pd.DataFrame, est) -> Linear:
    return Linear(est.fit(df[NUMERIC], df["target"].astype(int)))


def batch(index: int, gate: str = "passed", lag: int = 3, seed: int = 0) -> BatchView:
    apps = synthetic_batch(4000, seed=seed + index)
    apps["loan_key"] = [f"b{index}-{i}" for i in range(len(apps))]
    y = (np.random.default_rng(index).random(len(apps)) < risk(apps)).astype(float)
    labels = pd.DataFrame({"loan_key": apps["loan_key"], "target": y, "label_batch": index + lag})
    return BatchView(index, gate, apps, apps[["loan_key"]], labels)


def test_training_refuses_batches_without_contract_stamp() -> None:
    views = [batch(i, gate="blocked" if i == 2 else "passed") for i in range(6)]
    rows = challenger_rows(views, 8, CFG)
    assert 2 not in set(rows["cohort"]) and set(rows["cohort"]) == {3, 4, 5}


def test_training_refuses_immature_labels() -> None:
    views = [batch(i) for i in range(6)]
    with pytest.raises(TrainingRefusedError):
        challenger_rows(views, 2, CFG)  # nothing matured yet (lag 3)
    assert set(recalibration_rows(views, 6, CFG)["cohort"]) == {3}


def test_recalibration_fixes_a_shifted_risk() -> None:
    rows = pd.concat([batch(i).applications for i in range(2)], ignore_index=True)
    rows["target"] = (
        np.random.default_rng(9).random(len(rows)) < np.minimum(1, 1.6 * risk(rows))
    ).astype(int)
    honest = (np.random.default_rng(1).random(len(rows)) < risk(rows)).astype(int)
    base = fit(rows.assign(target=honest), LogisticRegression())
    recal = fit_recalibration(
        base, rows.assign(**{c: rows[c] for c in model_feature_columns()}), CFG
    )
    before = rows["target"].mean() / base.predict_proba(rows)[:, 1].mean()
    after = rows["target"].mean() / recal.predict_proba(rows)[:, 1].mean()
    assert before > 1.3 and abs(after - 1) < 0.05


def test_gate_rejects_a_worse_challenger() -> None:
    data = pd.concat([batch(i).applications.assign(target=batch(i).labels["target"].to_numpy())
                      for i in range(4)], ignore_index=True)  # fmt: skip
    champion = fit(data, LogisticRegression())
    worse = fit(data, DummyClassifier(strategy="prior"))
    out = evaluate_gate(champion, worse, data.iloc[:4000], data.iloc[4000:8000], 0.5, CFG)
    assert not out["passed"] and not out["checks"]["auc_gain_recent"]["passed"]


@pytest.fixture
def registry(tmp_path: Path):
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}")
    exp = mlflow.create_experiment("response", artifact_location=tmp_path.as_uri())
    data = batch(0).applications.assign(target=batch(0).labels["target"].to_numpy())
    versions = []
    with mlflow.start_run(experiment_id=exp):
        for _ in range(2):
            est = LogisticRegression().fit(data[NUMERIC], data["target"])
            info = mlflow.sklearn.log_model(est, name="m", skops_trusted_types=["numpy.dtype"])
            versions.append(str(mlflow.register_model(info.model_uri, "drill").version))
    yield versions
    mlflow.set_tracking_uri(previous)


def test_promote_then_rollback_restores_and_is_reversible(registry: list[str]) -> None:
    v1, v2 = registry
    mlflow.MlflowClient().set_registered_model_alias("drill", "champion", v1)
    assert promote("drill", v2, "champion_previous") == {"champion": v2, "champion_previous": v1}
    rollback("drill", "champion_previous")
    assert (
        alias_version("drill", "champion") == v1
        and alias_version("drill", "champion_previous") == v2
    )
    rollback("drill", "champion_previous")
    assert alias_version("drill", "champion") == v2


def test_rollback_without_previous_version_fails(registry: list[str]) -> None:
    mlflow.MlflowClient().set_registered_model_alias("drill", "champion", registry[0])
    with pytest.raises(RuntimeError):
        rollback("drill", "never_set")


def period(scores: np.ndarray, target: np.ndarray, level: int = 2, diag: str = "D2") -> cmp.Period:
    frame = synthetic_batch(len(scores), seed=4).assign(target=target, score=scores)
    signals = dict.fromkeys(cmp.SIGNALS_L34, 0) | {"bad_rate_ratio": level}
    ev = {"index": 0, "diagnosis": diag, "severity": {"level": level, "signals": signals},
          "l4": {"bad_rate_ratio": 1.4}}  # fmt: skip
    return cmp.Period(0, frame, ev)


class FixedScores:
    """Model stub returning a given score vector (rows in the same order)."""

    def __init__(self, p: np.ndarray) -> None:
        self.p = p

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        return np.column_stack([1 - self.p, self.p])


def test_decision_point_and_value_of_review() -> None:
    policy, cost = load_policy(), load_cost_config()
    quiet = {
        "index": 0,
        "diagnosis": "none",
        "severity": {"level": 0, "signals": dict.fromkeys(cmp.SIGNALS_L34, 0)},
    }
    s = np.linspace(0.05, 0.45, 200)
    p = period(s, (np.arange(200) % 4 == 0).astype(int))
    assert cmp.decision_point([quiet, {**p.evidence, "index": 1}], policy) == (1, True)
    model = FixedScores(s)
    recover = cmp.threshold_decider(model, 0.495)
    nothing = cmp.run_strategy([p], recover, cost, recover)
    value = cmp.run_strategy([p], cmp.value_decider(model, 0.495, cost, policy), cost, recover)
    assert value["review"] > 0 and value["value_review_recovered"] == pytest.approx(
        nothing["value"]
    )


class Scaled:
    """Wrap a model and scale its default probability (to make it miscalibrated)."""

    def __init__(self, base, factor: float) -> None:
        self.base, self.factor = base, factor

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        p = np.minimum(1.0, self.factor * self.base.predict_proba(x)[:, 1])
        return np.column_stack([1 - p, p])


def test_gate_calibration_is_relative_to_the_champion() -> None:
    data = pd.concat([batch(i).applications.assign(target=batch(i).labels["target"].to_numpy())
                      for i in range(4)], ignore_index=True)  # fmt: skip
    model = fit(data, LogisticRegression())
    recent, ref = data.iloc[:4000], data.iloc[4000:8000]
    champion = Scaled(model, 0.6)  # far from calibrated
    better = Scaled(model, 0.85)  # still > 1 p.p. off, but closer than the champion
    worse = Scaled(model, 0.5)
    ok = evaluate_gate(champion, better, recent, ref, 0.5, CFG)["checks"]["calibration_gap_pp"]
    bad = evaluate_gate(champion, worse, recent, ref, 0.5, CFG)["checks"]["calibration_gap_pp"]
    assert ok["value"] > CFG.gate["max_calibration_gap_pp"] and ok["passed"]
    assert not bad["passed"]
