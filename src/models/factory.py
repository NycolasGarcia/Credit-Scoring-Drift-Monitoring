"""Model factory: build an unfitted scikit-learn pipeline from a model name and params."""

from collections.abc import Callable
from typing import Any

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.data.features import CATEGORICAL_FEATURES, numeric_features


def _log1p_nonneg(values: np.ndarray) -> np.ndarray:
    return np.log1p(np.clip(values, 0, None))


def _onehot() -> Pipeline:
    return make_pipeline(
        SimpleImputer(strategy="most_frequent"),
        OneHotEncoder(handle_unknown="ignore", min_frequency=50),
    )


def _linear_preprocessor(log_features: list[str]) -> ColumnTransformer:
    """Median imputation with missing indicators, log1p for money amounts, scaling, one-hot."""
    numeric = numeric_features()
    logged = [c for c in numeric if c in log_features]
    plain = [c for c in numeric if c not in log_features]
    log_pipe = make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True),
        FunctionTransformer(_log1p_nonneg),
        StandardScaler(),
    )
    num_pipe = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler())
    return ColumnTransformer(
        [
            ("log", log_pipe, logged),
            ("num", num_pipe, plain),
            ("cat", _onehot(), list(CATEGORICAL_FEATURES)),
        ]
    )


def _tree_preprocessor() -> ColumnTransformer:
    """Trees handle NaN natively; only categoricals need encoding."""
    return ColumnTransformer(
        [("num", "passthrough", numeric_features()), ("cat", _onehot(), list(CATEGORICAL_FEATURES))]
    )


def _dummy(params: dict, seed: int, log_features: list[str]) -> Pipeline:
    return make_pipeline(_tree_preprocessor(), DummyClassifier(**params, random_state=seed))


def _logreg(params: dict, seed: int, log_features: list[str]) -> Pipeline:
    return make_pipeline(
        _linear_preprocessor(log_features), LogisticRegression(**params, random_state=seed)
    )


def _xgboost(params: dict, seed: int, log_features: list[str]) -> Pipeline:
    model = XGBClassifier(**params, random_state=seed, n_jobs=-1, eval_metric="logloss")
    return make_pipeline(_tree_preprocessor(), model)


BUILDERS: dict[str, Callable[[dict, int, list[str]], Pipeline]] = {
    "dummy": _dummy,
    "logreg": _logreg,
    "xgboost": _xgboost,
}


def build_model(name: str, params: dict[str, Any], seed: int, log_features: list[str]) -> Pipeline:
    """Return an unfitted pipeline for ``name``.

    Raises:
        KeyError: if the model name is not registered in the factory.
    """
    if name not in BUILDERS:
        raise KeyError(f"unknown model '{name}'; available: {sorted(BUILDERS)}")
    return BUILDERS[name](params, seed, log_features)
