"""S5 — natural production: real monthly vintages, no injected drift, real label lag.

A label is observable only if the loan is mature at the snapshot (ADR-0004), and only from
its maturity month on (issue month + term, in batch units).
"""

from collections.abc import Iterator

import numpy as np
import pandas as pd

from src.contracts.schema import KEY, to_application_batch
from src.simulation.engine import TARGET, SimBatch
from src.simulation.settings import ScenarioConfig


def natural_labels(rows: pd.DataFrame, t: int) -> pd.DataFrame:
    """Labels of one real vintage: NaN where immature, label month = t + term."""
    known = (rows["is_mature"] & rows[TARGET].notna()).to_numpy()
    target = np.where(known, rows[TARGET].to_numpy(dtype=float), np.nan)
    label_batch = pd.array(np.where(known, t + rows["term"].to_numpy(), 0), dtype="Int64")
    label_batch[~known] = pd.NA
    return pd.DataFrame({KEY: rows[KEY].to_numpy(), TARGET: target, "p_oracle": np.nan,
                         "label_batch": label_batch})  # fmt: skip


def natural_batches(cfg: ScenarioConfig, production: pd.DataFrame) -> Iterator[SimBatch]:
    """One batch per real month in ``cfg.months``."""
    start, end = cfg.months
    for t, month in enumerate(pd.period_range(start, end, freq="M")):
        rows = production[production["vintage"] == str(month)].reset_index(drop=True)
        yield SimBatch(t, f"{cfg.id}-b{t:02d}", str(month), 0.0,
                       to_application_batch(rows), natural_labels(rows, t))  # fmt: skip
