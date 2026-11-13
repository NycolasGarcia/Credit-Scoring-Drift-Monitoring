"""Model factory, metrics, calibration, threshold and selection on synthetic data."""

import numpy as np
import pandas as pd
import pytest
import skops.io as sio

from src.data.features import CATEGORICAL_FEATURES, model_feature_columns
from src.models.calibration import calibrate, choose_calibration
from src.models.evaluate import CandidateResult, select_champion
from src.models.factory import build_model
from src.models.metrics import classification_metrics, decision_metrics, ks_statistic
from src.models.settings import CostConfig, Grid, load_cost_config, load_training_config
from src.models.threshold import (
    best_value_threshold,
    cost_sensitivity,
    expected_value,
    loan_economics,
)

CFG = load_training_config()


def synthetic_xy(n: int = 800, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    """Features with real names; risk driven by int_rate and dti."""
    rng = np.random.default_rng(seed)
    x = pd.DataFrame({c: rng.normal(size=n) for c in model_feature_columns()})
    for c in CATEGORICAL_FEATURES:
        x[c] = rng.choice(["A", "B", "C"], n)
    x.loc[rng.random(n) < 0.1, "dti"] = np.nan
    logit = -1.7 + 1.2 * x["int_rate"] + 0.6 * x["dti"].fillna(0)
    y = pd.Series((rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int))
    return x, y


def test_ks_known_values() -> None:
    y = np.array([0, 0, 1, 1])
    assert ks_statistic(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert ks_statistic(y, np.array([0.5, 0.5, 0.5, 0.5])) == 0.0


def test_classification_metrics_relations() -> None:
    y, p = np.array([0, 1, 0, 1, 0]), np.array([0.1, 0.9, 0.2, 0.6, 0.4])
    m = classification_metrics(y, p)
    assert m["gini"] == pytest.approx(2 * m["auc"] - 1)
    assert m["bad_rate_expected"] == pytest.approx(p.mean())


def test_decision_metrics_approve_below_threshold() -> None:
    out = decision_metrics(np.array([0, 1, 0, 1]), np.array([0.1, 0.2, 0.7, 0.9]), 0.5)
    assert out == {"approval_rate": 0.5, "bad_rate_approved": 0.5}


@pytest.mark.parametrize("name", ["dummy", "logreg", "xgboost"])
def test_factory_builds_fittable_pipelines(name: str) -> None:
    x, y = synthetic_xy()
    model = build_model(name, CFG.models[name], 0, CFG.log_features).fit(x, y)
    p = model.predict_proba(x)[:, 1]
    assert p.shape == (len(x),) and np.all((p >= 0) & (p <= 1))


def test_factory_rejects_unknown_model() -> None:
    with pytest.raises(KeyError, match="unknown model"):
        build_model("svm", {}, 0, [])


def test_real_models_beat_dummy_on_signal() -> None:
    x, y = synthetic_xy(2000)
    auc = {
        n: classification_metrics(
            y.to_numpy(),
            build_model(n, CFG.models[n], 0, CFG.log_features).fit(x, y).predict_proba(x)[:, 1],
        )["auc"]
        for n in ("dummy", "logreg")
    }
    assert auc["logreg"] > auc["dummy"] + 0.1


@pytest.mark.parametrize("method", ["sigmoid", "isotonic"])
def test_calibrated_models_load_with_trusted_type_allowlist(method: str) -> None:
    x, y = synthetic_xy()
    for name in ("logreg", "xgboost"):
        model = calibrate(
            build_model(name, CFG.models[name], 0, CFG.log_features).fit(x, y), x, y, method
        )
        restored = sio.loads(sio.dumps(model), trusted=CFG.skops_trusted_types)
        np.testing.assert_allclose(restored.predict_proba(x), model.predict_proba(x))


def test_choose_calibration_reports_raw_and_methods() -> None:
    x, y = synthetic_xy()
    model = build_model("logreg", CFG.models["logreg"], 0, CFG.log_features).fit(x, y)
    method, _, briers = choose_calibration(model, x, y, x, y, ["sigmoid", "isotonic"])
    assert set(briers) == {"raw", "sigmoid", "isotonic"}
    assert briers[method] == min(briers["sigmoid"], briers["isotonic"])


def test_loan_economics_and_expected_value() -> None:
    cost = CostConfig(status="PROPOSTO", lgd=0.5, margin_realization=1.0,
                      threshold_grid=Grid(start=0.1, stop=0.9, step=0.1))  # fmt: skip
    df = pd.DataFrame(
        {"installment": [110.0, 110.0], "term": [10.0, 10.0], "loan_amnt": [1000.0, 1000.0]}
    )
    gain, loss = loan_economics(df, cost)
    assert gain.tolist() == [100.0, 100.0] and loss.tolist() == [500.0, 500.0]
    y, p = np.array([0, 1]), np.array([0.2, 0.8])
    assert expected_value(y, p, gain, loss, 0.5) == 50.0
    assert expected_value(y, p, gain, loss, 0.9) == -200.0
    t, v = best_value_threshold(y, p, gain, loss, np.array([0.5, 0.9]))
    assert (t, v) == (0.5, 50.0)


def test_cost_sensitivity_moves_threshold_in_the_right_direction() -> None:
    rng = np.random.default_rng(3)
    n = 3000
    p = rng.random(n) * 0.6
    y = (rng.random(n) < p).astype(int)
    df = pd.DataFrame({"installment": 110.0, "term": 36.0, "loan_amnt": 3000.0}, index=range(n))
    out = cost_sensitivity(df, y, p, load_cost_config(), lgds=[0.3, 0.9], margins=[0.5])
    low_lgd, high_lgd = out["threshold"].tolist()
    assert low_lgd > high_lgd  # cheaper defaults -> approve more


def test_cost_config_is_marked_proposed() -> None:
    assert load_cost_config().status == "PROPOSTO"


def _cand(name: str, auc: float, psi: float) -> CandidateResult:
    c = CandidateResult(name, "run", None, "none", {})
    c.metrics, c.score_psi = {"test": {"auc": auc}}, {"oot": psi}
    return c


def test_selection_prefers_stability_within_tie() -> None:
    picked = select_champion([_cand("dummy", 0.5, 0.0), _cand("logreg", 0.700, 0.20),
                              _cand("xgboost", 0.702, 0.30)], CFG)  # fmt: skip
    assert picked.name == "logreg"


def test_selection_prefers_auc_outside_tie() -> None:
    picked = select_champion([_cand("dummy", 0.5, 0.0), _cand("logreg", 0.70, 0.10),
                              _cand("xgboost", 0.75, 0.30)], CFG)  # fmt: skip
    assert picked.name == "xgboost"


def test_selection_rejects_candidate_not_beating_dummy() -> None:
    with pytest.raises(ValueError, match="dummy"):
        select_champion([_cand("dummy", 0.6, 0.0), _cand("logreg", 0.55, 0.1)], CFG)
