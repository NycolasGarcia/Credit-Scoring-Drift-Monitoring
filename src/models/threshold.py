"""Decision economics and the expected-value approval threshold (ADR-0007)."""

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from src.models.settings import CostConfig


def loan_economics(df: pd.DataFrame, cost: CostConfig) -> tuple[np.ndarray, np.ndarray]:
    """Per-loan gain if a good loan is approved and loss if a bad loan is approved.

    Uses origination fields only: contractual interest = installment * term - loan_amnt.
    """
    interest = (df["installment"] * df["term"] - df["loan_amnt"]).clip(lower=0)
    gain = (interest * cost.margin_realization).to_numpy()
    loss = (df["loan_amnt"] * cost.lgd).to_numpy()
    return gain, loss


def expected_value(
    y: np.ndarray, p: np.ndarray, gain: np.ndarray, loss: np.ndarray, threshold: float
) -> float:
    """Realized value per application of approving everyone scored below ``threshold``."""
    approved = p < threshold
    value = np.where(y == 1, -loss, gain) * approved
    return float(value.sum() / len(y))


def threshold_grid(cost: CostConfig) -> np.ndarray:
    """Candidate thresholds from the cost config."""
    g = cost.threshold_grid
    return np.round(np.arange(g.start, g.stop + g.step / 2, g.step), 6)


def best_value_threshold(
    y: np.ndarray, p: np.ndarray, gain: np.ndarray, loss: np.ndarray, grid: np.ndarray
) -> tuple[float, float]:
    """Threshold maximizing value per application, and that value."""
    values = np.array([expected_value(y, p, gain, loss, t) for t in grid])
    best = int(np.argmax(values))
    return float(grid[best]), float(values[best])


def best_f1_threshold(y: np.ndarray, p: np.ndarray, grid: np.ndarray) -> float:
    """Threshold maximizing F1 for the bad class (flag as bad when score >= threshold)."""
    scores = [f1_score(y, (p >= t).astype(int), zero_division=0) for t in grid]
    return float(grid[int(np.argmax(scores))])
