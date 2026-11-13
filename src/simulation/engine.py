"""Scenario engine: holdout -> monthly batches with controlled drift and known ground truth.

Pure: (config, base, profile, risk function) -> batches. Every batch draws from its own
generator seeded by (scenario seed, batch index), so a batch is reproducible on its own.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.contracts.schema import KEY, to_application_batch
from src.simulation.labels import relabel, shifted_risk
from src.simulation.settings import ScenarioConfig
from src.simulation.transforms import apply_bugs, apply_real, intensity, logit_delta

RiskFn = Callable[[pd.DataFrame], np.ndarray]
TARGET = "target"


@dataclass
class SimBatch:
    """One monthly batch: what production sees (applications) and what it learns later."""

    index: int
    batch_id: str
    issue_month: str
    level: float
    applications: pd.DataFrame
    labels: pd.DataFrame
    bug_rows: int = 0


@dataclass(frozen=True)
class SimContext:
    """Inputs shared by every batch of a scenario."""

    cfg: ScenarioConfig
    base: pd.DataFrame
    profile: dict[str, Any]
    risk: RiskFn


def batch_rng(seed: int, t: int) -> np.random.Generator:
    """Independent, reproducible generator for batch ``t``."""
    return np.random.default_rng([seed, t])


def month_of(cfg: ScenarioConfig, t: int) -> pd.Period:
    """Calendar month of batch ``t``."""
    return pd.Period(cfg.calendar_start, freq="M") + t


def _draw(ctx: SimContext, t: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = rng.choice(len(ctx.base), size=ctx.cfg.batch_size, replace=False)
    out = ctx.base.iloc[np.sort(rows)].reset_index(drop=True)
    out[KEY] = [f"{ctx.cfg.id}-{t:02d}-{i:05d}" for i in range(len(out))]
    out["issue_d"] = month_of(ctx.cfg, t).to_timestamp()
    return out


def _labels(
    ctx: SimContext, orig: pd.DataFrame, true_x: pd.DataFrame, level: float, t: int, rng
) -> pd.DataFrame:
    p_old = ctx.risk(orig)
    p_base = ctx.risk(true_x) if level > 0 else p_old
    p_new = shifted_risk(p_base, logit_delta(true_x, ctx.cfg.transforms, level, ctx.profile))
    y = relabel(orig[TARGET].to_numpy(dtype=int), p_old, p_new, rng)
    return pd.DataFrame({KEY: orig[KEY], TARGET: y.astype(float), "p_oracle": p_new,
                         "label_batch": t + ctx.cfg.label_lag})  # fmt: skip


def simulate_batch(ctx: SimContext, t: int) -> SimBatch:
    """Build batch ``t``: draw, change the world, corrupt the feed, move the labels."""
    rng, level = batch_rng(ctx.cfg.seed, t), intensity(ctx.cfg.schedule, t)
    orig = _draw(ctx, t, rng)
    true_x = apply_real(orig, ctx.cfg.transforms, level)
    observed, hit = apply_bugs(true_x, ctx.cfg.transforms, level, rng)
    labels = _labels(ctx, orig, true_x, level, t, rng)
    return SimBatch(t, f"{ctx.cfg.id}-b{t:02d}", str(month_of(ctx.cfg, t)), level,
                    to_application_batch(observed), labels, int(hit.sum()))  # fmt: skip


def simulate(ctx: SimContext) -> Iterator[SimBatch]:
    """All batches of a holdout-based scenario, in time order."""
    for t in range(ctx.cfg.batches):
        yield simulate_batch(ctx, t)
