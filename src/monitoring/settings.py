"""Validated monitoring thresholds (``config/monitoring/thresholds.yaml``)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from src.config import PROJECT_ROOT

THRESHOLDS_PATH = PROJECT_ROOT / "config" / "monitoring" / "thresholds.yaml"
Status = Literal["PROPOSTO", "CALIBRADO"]
Signal = Literal[
    "feature_psi", "score_psi", "approval_delta_pp", "bad_rate_ratio", "auc_drop", "segment_gap"
]


class Threshold(BaseModel):
    """One signal's severity cut points (higher value = worse)."""

    id: str
    signal: Signal
    layer: Literal["L2", "L3", "L4"]
    direction: Literal["higher_is_worse", "two_sided", "symmetric_ratio"] = "higher_is_worse"
    sev1: float
    sev2: float | None = None
    sev3: float | None = None
    sev3_min_features: int | None = None
    status: Status
    calibration_run: str | None = None
    rationale: str


class FalseAlarmTarget(BaseModel):
    """Maximum share of control batches allowed to alert, per severity."""

    sev1: float = Field(ge=0, le=1)
    sev2: float = Field(ge=0, le=1)
    status: Status


class CalibrationParams(BaseModel):
    """Bootstrap of control batches."""

    replicates: int = Field(ge=50)
    batch_size: int = Field(ge=100)
    seed: int


class DiagnosisParams(BaseModel):
    """Unit-bug (D6) signature parameters."""

    unit_factors: list[float]
    tail_quantile: float = Field(gt=0, lt=0.5)
    min_tail_excess: float = Field(gt=0, lt=1)
    max_psi_ratio: float = Field(gt=0, lt=1)
    status: Status


class MonitoringConfig(BaseModel):
    """Whole thresholds file."""

    version: int
    false_alarm_target: FalseAlarmTarget
    calibration: CalibrationParams
    top_k_features: int = Field(ge=1)
    thresholds: list[Threshold]
    diagnosis: DiagnosisParams
    min_labeled_rows: int = Field(ge=10)

    def get(self, signal: str) -> Threshold:
        """Threshold of one signal."""
        return next(t for t in self.thresholds if t.signal == signal)


def load_monitoring_config(path: Path = THRESHOLDS_PATH) -> MonitoringConfig:
    """Load and validate the thresholds YAML."""
    with path.open(encoding="utf-8") as fh:
        return MonitoringConfig.model_validate(yaml.safe_load(fh))


@lru_cache(maxsize=1)
def monitoring_config() -> MonitoringConfig:
    """Cached config for the default path."""
    return load_monitoring_config()
