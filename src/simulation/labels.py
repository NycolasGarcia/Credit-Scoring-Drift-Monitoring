"""Label mechanism: move each observed label from risk ``p_old`` to risk ``p_new``.

The reference P(default | X) is estimated by the calibrated champion (the "oracle"). For a
row with true risk ``p_old`` and a known 0/1 outcome, flipping

    0 -> 1 with probability (p_new - p_old) / (1 - p_old)   when p_new > p_old
    1 -> 0 with probability (p_old - p_new) / p_old         when p_new < p_old

gives E[y_new | x] = p_new exactly, while keeping the real outcome whenever risk is unchanged.
"""

import numpy as np

EPS = 1e-6


def logit(p: np.ndarray) -> np.ndarray:
    """Log-odds with clipping away from 0 and 1."""
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def shifted_risk(p: np.ndarray, delta: np.ndarray) -> np.ndarray:
    """Risk after adding ``delta`` to the logit."""
    return 1 / (1 + np.exp(-(logit(p) + delta)))


def relabel(
    y: np.ndarray, p_old: np.ndarray, p_new: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """Return labels whose conditional mean moves from ``p_old`` to ``p_new``."""
    p_old = np.clip(p_old, EPS, 1 - EPS)
    u = rng.random(len(y))
    up = (p_new > p_old) & (y == 0) & (u < (p_new - p_old) / (1 - p_old))
    down = (p_new < p_old) & (y == 1) & (u < (p_old - p_new) / p_old)
    out = y.copy()
    out[up], out[down] = 1, 0
    return out
