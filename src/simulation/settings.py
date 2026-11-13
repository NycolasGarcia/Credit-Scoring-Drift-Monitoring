"""Validated scenario configuration (``config/scenarios/S*.yaml``).

A scenario states what changes (transforms), when (schedule) and what the detector is
expected to see (``expected``). No magnitude lives in code.
"""

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from src.config import PROJECT_ROOT

SCENARIO_DIR = PROJECT_ROOT / "config" / "scenarios"
Layer = Literal["L0", "L1", "L2", "L3", "L4"]


class Schedule(BaseModel):
    """Intensity over time: 0 before ``onset``, then sudden, gradual or recurrent."""

    shape: Literal["none", "sudden", "gradual", "recurrent"]
    onset: int = Field(0, ge=0)
    ramp: int = Field(1, ge=1, description="batches to reach full intensity (gradual)")
    period: int = Field(2, ge=2, description="on/off cycle length in batches (recurrent)")


class Scale(BaseModel):
    """Real-world change: feature multiplied by ``factor`` at full intensity."""

    kind: Literal["scale"]
    feature: str
    factor: float = Field(gt=0)


class Shift(BaseModel):
    """Real-world change: ``delta`` added to the feature at full intensity."""

    kind: Literal["shift"]
    feature: str
    delta: float


class UnitBug(BaseModel):
    """Upstream bug: a share of rows arrives divided by ``divisor``; reality is unchanged."""

    kind: Literal["unit_bug"]
    feature: str
    divisor: float = Field(gt=0)
    fraction: float = Field(gt=0, le=1)


class Segment(BaseModel):
    """Rows whose feature is at or above a reference decile edge."""

    feature: str
    min_quantile: float = Field(ge=0.1, le=0.9)

    @model_validator(mode="after")
    def _decile(self) -> "Segment":
        if abs(self.min_quantile * 10 - round(self.min_quantile * 10)) > 1e-9:
            raise ValueError("min_quantile must be a decile (0.1 ... 0.9)")
        return self

    @property
    def edge_index(self) -> int:
        """Index of the decile edge in the reference profile (0.1 -> 0)."""
        return round(self.min_quantile * 10) - 1


class LogitShift(BaseModel):
    """Label mechanism change: logit of P(default | X) shifted by ``delta`` (X unchanged)."""

    kind: Literal["logit_shift"]
    delta: float
    segment: Segment | None = None


Transform = Annotated[Scale | Shift | UnitBug | LogitShift, Field(discriminator="kind")]


class Expected(BaseModel):
    """Ground truth stated by design: layers that should fire and the right diagnosis."""

    layers: list[Layer]
    diagnosis: Literal["none", "D1", "D2", "D3", "D6", "unknown"]


class ScenarioConfig(BaseModel):
    """One degradation scenario."""

    id: str = Field(pattern=r"^S\d$")
    name: str
    drift_type: Literal["none", "D1", "D2", "D3", "D6", "natural"]
    narrative: str
    source: Literal["holdout", "production"]
    seed: int
    label_lag: int = Field(ge=0, description="batches until a simulated label is observable")
    calendar_start: str = Field(pattern=r"^\d{4}-\d{2}$")
    batches: int = Field(1, ge=1)
    batch_size: int = Field(1, ge=1)
    months: tuple[str, str] | None = None
    schedule: Schedule
    transforms: list[Transform] = Field(default_factory=list)
    expected: Expected

    @model_validator(mode="after")
    def _source_fields(self) -> "ScenarioConfig":
        if self.source == "production" and (self.months is None or self.transforms):
            raise ValueError("production scenarios need `months` and take no transforms")
        return self


def load_scenario(scenario_id: str, folder: Path = SCENARIO_DIR) -> ScenarioConfig:
    """Load and validate ``<folder>/<id>.yaml``."""
    with (folder / f"{scenario_id}.yaml").open(encoding="utf-8") as fh:
        return ScenarioConfig.model_validate(yaml.safe_load(fh))


def scenario_ids(folder: Path = SCENARIO_DIR) -> list[str]:
    """All configured scenario ids, sorted."""
    return sorted(p.stem for p in folder.glob("S*.yaml"))
