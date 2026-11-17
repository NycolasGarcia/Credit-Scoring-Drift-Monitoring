"""Validated alert catalog (``config/monitoring/alerts.yaml``, ADR-0011)."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from src.config import PROJECT_ROOT

ALERTS_PATH = PROJECT_ROOT / "config" / "monitoring" / "alerts.yaml"
Source = Literal[
    "signal", "gate", "soft_rules", "unit_bug", "step_failed", "slow", "staleness", "fairness"
]


class Staleness(BaseModel):
    """Dead man's switch: alert when no success for ``multiple`` x the expected interval."""

    expected_interval_seconds: float = Field(gt=0)
    multiple: float = Field(gt=1)

    @property
    def limit_seconds(self) -> float:
        """Seconds without a successful batch before the alert fires."""
        return self.expected_interval_seconds * self.multiple


class Slow(BaseModel):
    """Batch duration alert."""

    duration_multiple: float = Field(gt=1)


class Alert(BaseModel):
    """One alert: where its level comes from and what to do about it."""

    id: str = Field(pattern=r"^CDM_[A-Z0-9_]+$")
    title: str
    source: Source
    signal: str | None = None
    layer: Literal["L0", "L1", "L2", "L3", "L4"]
    diagnosis: Literal["D0", "D1", "D2", "D3", "D4", "D5", "D6"]
    action: str

    @model_validator(mode="after")
    def _signal_only_for_signal_source(self) -> "Alert":
        if (self.source == "signal") != (self.signal is not None):
            raise ValueError(f"{self.id}: `signal` is required iff source == 'signal'")
        return self

    @property
    def anchor(self) -> str:
        """Playbook anchor in the runbook (GitHub heading slug)."""
        return self.id.lower()


class AlertConfig(BaseModel):
    """Whole alert catalog."""

    version: int
    owner: str
    runbook: str
    staleness: Staleness
    slow: Slow
    alerts: list[Alert]


def load_alert_config(path: Path = ALERTS_PATH) -> AlertConfig:
    """Load and validate the alert catalog."""
    with path.open(encoding="utf-8") as fh:
        return AlertConfig.model_validate(yaml.safe_load(fh))
