"""Post-hoc probability calibration on a held-out calibration set."""

import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import brier_score_loss


def calibrate(model: ClassifierMixin, x_cal, y_cal, method: str) -> CalibratedClassifierCV:
    """Fit a calibrator ("sigmoid" = Platt, "isotonic") on top of an already fitted model."""
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method=method)
    return calibrated.fit(x_cal, y_cal)


def choose_calibration(
    model: ClassifierMixin, x_cal, y_cal, x_eval, y_eval, methods: list[str]
) -> tuple[str, CalibratedClassifierCV, dict[str, float]]:
    """Calibrate with each method and keep the one with the lowest Brier on the eval set.

    Returns:
        Chosen method name, fitted calibrated model, and Brier per method (``raw`` included).
    """
    briers = {"raw": float(brier_score_loss(y_eval, model.predict_proba(x_eval)[:, 1]))}
    fitted = {}
    for method in methods:
        fitted[method] = calibrate(model, x_cal, y_cal, method)
        p = fitted[method].predict_proba(x_eval)[:, 1]
        briers[method] = float(brier_score_loss(y_eval, np.asarray(p)))
    best = min(methods, key=lambda m: briers[m])
    return best, fitted[best], briers
