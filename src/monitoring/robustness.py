"""Robustness of the detector and of the responses over fresh seeds and magnitudes (pure).

Every variant is an official scenario with another seed and its intensity multiplied by ``m``
(1.0 = official). The reading rule lives in ``config/monitoring/robustness.yaml`` and is
declared before the run; this module only applies it.
"""

import math
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pydantic import BaseModel

from src.config import PROJECT_ROOT
from src.simulation.settings import ScenarioConfig

ROBUSTNESS_PATH = PROJECT_ROOT / "config" / "monitoring" / "robustness.yaml"


class Reading(BaseModel):
    """Declared reading rule."""

    detected_level: int
    min_detection_share: float
    min_diagnosis_lower: float
    max_false_alarm_sev2: float
    response_min_positive: float


class RobustnessConfig(BaseModel):
    """Whole robustness file."""

    version: int
    status: str
    seeds: list[int]
    magnitudes: list[float]
    scenarios: list[str]
    control: str
    compare_magnitude: float
    reading: Reading


def load_robustness(path: Path = ROBUSTNESS_PATH) -> RobustnessConfig:
    """Load and validate the robustness YAML."""
    with path.open(encoding="utf-8") as fh:
        return RobustnessConfig.model_validate(yaml.safe_load(fh))


def _scaled(t: dict[str, Any], m: float) -> dict[str, Any]:
    kind = t["kind"]
    if kind == "scale":
        return {**t, "factor": 1 + (t["factor"] - 1) * m}
    if kind in ("shift", "logit_shift"):
        return {**t, "delta": t["delta"] * m}
    return {**t, "fraction": min(1.0, t["fraction"] * m)}  # unit_bug


def variant(base: ScenarioConfig, m: float, seed: int) -> ScenarioConfig:
    """Copy of an official scenario with another seed and intensity times ``m``."""
    raw = base.model_dump(mode="json")
    raw["seed"], raw["transforms"] = seed, [_scaled(t, m) for t in raw["transforms"]]
    return ScenarioConfig.model_validate(raw)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson score interval of a proportion (None without observations)."""
    if n == 0:
        return None
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def first_alert(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Index, level and diagnosis of the first alerting batch (to explain misdiagnoses)."""
    r = next((r for r in results if r["severity"]["level"] >= 1), None)
    return r and {"index": r["index"], "level": r["severity"]["level"], "diagnosis": r["diagnosis"]}


def detection_row(scenario: str, m: float, seed: int, results, evaluation) -> dict[str, Any]:
    """What one variant tells about the detector (aggregates only)."""
    onset, diag = evaluation["onset"], evaluation["diagnosis"]
    pre = [r for r in results if onset is None or r["index"] < onset]
    post = [r for r in results if onset is not None and r["index"] >= onset]
    blocked = sum(r["gate_status"] == "blocked" for r in post)  # caught by the contract (L0)
    return {"scenario": scenario, "m": m, "seed": seed, "onset": onset,
            "first_sev1": evaluation["first_sev1"], "first_sev2": evaluation["first_sev2"],
            "pre_batches": len(pre), "pre_sev1": sum(r["severity"]["level"] >= 1 for r in pre),
            "pre_sev2": sum(r["severity"]["level"] >= 2 for r in pre),
            "alerting": sum(diag["counts"].values()) - blocked,  # the detector's own alerts
            "blocked": blocked, "correct": diag["counts"].get(diag["expected"], 0),
            "recall": evaluation["attribution"]["recall"], "diagnoses": diag["counts"],
            "first_alert": first_alert(results)}  # fmt: skip


def summarize_cell(rows: list[dict[str, Any]], level: int) -> dict[str, Any]:
    key = "first_sev2" if level >= 2 else "first_sev1"
    hits = [r for r in rows if r[key] is not None]
    k, n = sum(r["correct"] for r in rows), sum(r["alerting"] for r in rows)
    ci = wilson(k, n)
    delays = [r[key] - r["onset"] for r in hits]
    return {
        "seeds": len(rows),
        "detected": len(hits),
        "sev1_detected": sum(r["first_sev1"] is not None for r in rows),
        "median_delay": float(np.median(delays)) if delays else None,
        "diagnosis_correct": k,
        "diagnosis_alerting": n,
        "diagnosis_ci": list(ci) if ci else None,
        "blocked": sum(r.get("blocked", 0) for r in rows),
        "pre_batches": sum(r["pre_batches"] for r in rows),
        "pre_sev1": sum(r["pre_sev1"] for r in rows),
        "pre_sev2": sum(r["pre_sev2"] for r in rows),
    }


def verdict(cell: dict[str, Any], rule: Reading, control: bool = False) -> dict[str, bool | None]:
    """Declared rule applied to one (scenario, m) cell; detection does not apply to the control."""
    det = None if control else cell["detected"] / cell["seeds"] >= rule.min_detection_share
    ci = cell["diagnosis_ci"]
    fa = cell["pre_sev2"] / cell["pre_batches"] if cell["pre_batches"] else 0.0
    return {
        "detection": det,
        "diagnosis": None if ci is None else ci[0] >= rule.min_diagnosis_lower,
        "false_alarm": fa <= rule.max_false_alarm_sev2,
    }


def detection_summary(rows: list[dict[str, Any]], cfg: RobustnessConfig) -> list[dict[str, Any]]:
    """One cell per (scenario, m) with the declared verdict."""
    out = []
    for sid in [cfg.control, *cfg.scenarios]:
        for m in [0.0] if sid == cfg.control else cfg.magnitudes:
            cell = summarize_cell(
                [r for r in rows if r["scenario"] == sid and r["m"] == m],
                cfg.reading.detected_level,
            )
            v = verdict(cell, cfg.reading, control=sid == cfg.control)
            out.append({"scenario": sid, "m": m, **cell, "verdict": v})
    return out


def response_summary(rows: list[dict[str, Any]], rule: Reading) -> list[dict[str, Any]]:
    """Per scenario and strategy: delta vs. doing nothing over the seeds (US$)."""
    out = []
    for sid in sorted({r["scenario"] for r in rows}):
        sub = [r for r in rows if r["scenario"] == sid]
        for name in dict.fromkeys(s for r in sub for s in r["deltas"]):
            d = np.array([r["deltas"][name] for r in sub if name in r["deltas"]])
            positive = int((d > 0).sum())
            out.append(
                {
                    "scenario": sid,
                    "strategy": name,
                    "seeds": len(d),
                    "median": float(np.median(d)),
                    "min": float(d.min()),
                    "max": float(d.max()),
                    "positive": positive,
                    "robust": positive / len(d) >= rule.response_min_positive,
                }
            )
    return out
