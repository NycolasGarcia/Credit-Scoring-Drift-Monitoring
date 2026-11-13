"""Validated training and cost configuration (``config/models/*.yaml``)."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.config import PROJECT_ROOT

TRAINING_PATH = PROJECT_ROOT / "config" / "models" / "training.yaml"
COST_PATH = PROJECT_ROOT / "config" / "models" / "cost.yaml"


class InternalSplit(BaseModel):
    """Fractions of the reference partition held out from training."""

    calibration: float = Field(gt=0, lt=0.5)
    test: float = Field(gt=0, lt=0.5)


class Selection(BaseModel):
    """Model selection rule."""

    auc_tie_tolerance: float = Field(ge=0)


class Importance(BaseModel):
    """Permutation importance settings."""

    sample_rows: int = Field(gt=0)
    n_repeats: int = Field(gt=0)


class TrainingConfig(BaseModel):
    """All training parameters."""

    seed: int
    internal_split: InternalSplit
    cv_folds: int = Field(ge=2)
    oot_windows: dict[str, tuple[str, str]]
    log_features: list[str]
    models: dict[str, dict[str, Any]]
    calibration_methods: list[str]
    selection: Selection
    leakage_auc_ceiling: float
    importance: Importance
    registry_model_name: str
    skops_trusted_types: list[str]


class Grid(BaseModel):
    """Threshold search grid."""

    start: float
    stop: float
    step: float = Field(gt=0)


class CostConfig(BaseModel):
    """Decision economics premises."""

    status: str
    lgd: float = Field(gt=0, le=1)
    margin_realization: float = Field(gt=0, le=1)
    threshold_grid: Grid


def _read(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def load_training_config(path: Path = TRAINING_PATH) -> TrainingConfig:
    """Load ``training.yaml``."""
    return TrainingConfig.model_validate(_read(path))


@lru_cache(maxsize=1)
def load_cost_config(path: Path = COST_PATH) -> CostConfig:
    """Load ``cost.yaml``."""
    return CostConfig.model_validate(_read(path))
