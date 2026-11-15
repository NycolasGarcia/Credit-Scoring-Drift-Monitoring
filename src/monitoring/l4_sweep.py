"""SEV-2 cut of the observed/expected bad-rate ratio (L4): null-based choice, unseen-variant check.

The cut is chosen only from the null distribution (rule in ``config/monitoring/l4_sweep.yaml``,
declared before running). Fresh-seed variants of S2/S3 then measure whether the chosen cut
detects scenarios it never saw; existing scenario evidence shows side effects per cut.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel

from src.config import PROJECT_ROOT
from src.monitoring.settings import Threshold
from src.monitoring.severity import magnitude
from src.simulation.engine import SimContext, simulate
from src.simulation.settings import ScenarioConfig

SWEEP_PATH = PROJECT_ROOT / "config" / "monitoring" / "l4_sweep.yaml"


class NullParams(BaseModel):
    """Bootstrap of control cohorts."""

    replicates: int
    seed: int
    batch_sizes: list[int]


class Rule(BaseModel):
    """Choice rule, declared before the run."""

    max_null_alarm: float
    min_margin: float


class Variants(BaseModel):
    """Fresh-seed scenario variants used only for validation."""

    seeds: list[int]
    S2_deltas: list[float]
    S3_deltas: list[float]


class SweepConfig(BaseModel):
    """Whole sweep file."""

    version: int
    cuts: list[float]
    control: NullParams
    rule: Rule
    variants: Variants


def load_sweep_config(path: Path = SWEEP_PATH) -> SweepConfig:
    """Load and validate the sweep YAML."""
    with path.open(encoding="utf-8") as fh:
        return SweepConfig.model_validate(yaml.safe_load(fh))


def null_ratios(y: np.ndarray, p: np.ndarray, size: int, params: NullParams, th: Threshold):
    """Oriented ratio of ``replicates`` control cohorts of ``size`` rows."""
    rng = np.random.default_rng([params.seed, size])
    out = np.empty(params.replicates)
    for i in range(params.replicates):
        idx = rng.choice(len(y), size, replace=False)
        out[i] = magnitude(float(y[idx].mean() / p[idx].mean()), th)
    return out


def choose_cut(cfg: SweepConfig, null6000: np.ndarray) -> float | None:
    """Smallest grid cut with no null alarm and the declared margin over the null maximum."""
    ok = [c for c in cfg.cuts if (null6000 >= c).mean() <= cfg.rule.max_null_alarm
          and c >= null6000.max() + cfg.rule.min_margin]  # fmt: skip
    return min(ok) if ok else None


def variant(base: ScenarioConfig, delta: float, seed: int) -> ScenarioConfig:
    """Copy of an official scenario with another logit shift and seed."""
    raw = base.model_dump(mode="json")
    raw["transforms"][0]["delta"], raw["seed"] = delta, seed
    return ScenarioConfig.model_validate(raw)


def ratio_series(ctx: SimContext, risk: Callable[[pd.DataFrame], np.ndarray]) -> dict[int, float]:
    """Observed/expected ratio of the labels maturing at each batch."""
    parts = []
    for b in simulate(ctx):
        score = risk(b.applications)
        parts.append(b.labels.assign(score=score))
    hist = pd.concat(parts, ignore_index=True)
    return {int(t): float(g["target"].mean() / g["score"].mean())
            for t, g in hist.groupby("label_batch") if t < ctx.cfg.batches}  # fmt: skip


def first_at(series: dict[int, float], cut: float, th: Threshold) -> int | None:
    """First batch whose oriented ratio reaches ``cut``."""
    return next((t for t in sorted(series) if magnitude(series[t], th) >= cut), None)


def evidence_series(evidence: dict[str, Any]) -> dict[int, float]:
    """Ratio per batch already measured by the detector (batches with L4 only)."""
    return {b["index"]: b["l4"]["bad_rate_ratio"] for b in evidence["batches"] if b["l4"]}


def detection_table(
    runs: list[dict[str, Any]], cuts: list[float], th: Threshold
) -> list[dict[str, Any]]:
    """Per cut and scenario family: share of variants reaching the cut and median delay."""
    rows = []
    for cut in cuts:
        for fam in sorted({r["family"] for r in runs}):
            fam_runs = [r for r in runs if r["family"] == fam]
            firsts = [first_at(r["series"], cut, th) for r in fam_runs]
            delays = [
                f - r["onset"] for f, r in zip(firsts, fam_runs, strict=True) if f is not None
            ]
            rows.append({"cut": cut, "family": fam, "detected": sum(f is not None for f in firsts),
                         "variants": len(fam_runs),
                         "median_delay": float(np.median(delays)) if delays else None})  # fmt: skip
    return rows


def side_effects(
    evidences: dict[str, dict[str, Any]], cuts: list[float], th: Threshold
) -> list[dict[str, Any]]:
    """Batches at or above each cut in the scenarios already evaluated."""
    rows = []
    for sid, ev in evidences.items():
        series = evidence_series(ev)
        for cut in cuts:
            hits = sum(magnitude(v, th) >= cut for v in series.values())
            rows.append({"scenario": sid, "cut": cut, "batches_with_l4": len(series),
                         "batches_at_cut": hits})  # fmt: skip
    return rows


def null_summary(nulls: dict[int, np.ndarray], cuts: list[float]) -> dict[str, Any]:
    """Null maximum, q99 and alarm share per cut, for each cohort size."""
    return {str(n): {"max": float(v.max()), "q99": float(np.quantile(v, 0.99)),
                     "alarm": {str(c): float((v >= c).mean()) for c in cuts}}
            for n, v in nulls.items()}  # fmt: skip


def run_variants(
    cfg: SweepConfig,
    bases: dict[str, ScenarioConfig],
    ctx_of: Callable[[ScenarioConfig], SimContext],
) -> list[dict[str, Any]]:
    """Ratio series of every fresh-seed variant of S2 and S3."""
    runs = []
    grid = {"S2": cfg.variants.S2_deltas, "S3": cfg.variants.S3_deltas}
    for fam, deltas in grid.items():
        for delta in deltas:
            for seed in cfg.variants.seeds:
                vc = variant(bases[fam], delta, seed)
                ctx = ctx_of(vc)
                runs.append(
                    {
                        "family": f"{fam} delta={delta}",
                        "seed": seed,
                        "onset": vc.schedule.onset,
                        "series": ratio_series(ctx, ctx.risk),
                    }
                )
    return runs
