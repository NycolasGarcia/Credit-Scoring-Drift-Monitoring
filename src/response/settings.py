"""Validated response policy (``config/response/policy.yaml``, §8.5, ADR-0012)."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from src.config import PROJECT_ROOT

POLICY_PATH = PROJECT_ROOT / "config" / "response" / "policy.yaml"
ActionCode = Literal["A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9"]


class Condition(BaseModel):
    """When a rule applies (every given field must hold; empty = always)."""

    diagnosis: list[str] | None = None
    output_min_level: int | None = Field(None, ge=1, le=3)
    batch_min_level: int | None = Field(None, ge=1, le=3)


class Action(BaseModel):
    """One action of the §8.5 catalog and who executes it."""

    code: ActionCode
    mode: Literal["auto", "human"]


class Rule(BaseModel):
    """Row of the response matrix."""

    id: str
    when: Condition
    situation: str
    actions: list[Action]


class FairnessCap(BaseModel):
    """Largest approval gap between groups the conservative mode may open (ADR-0015)."""

    segments: list[str]  # grouped as in config/governance/fairness.yaml
    max_gap_pp: float = Field(gt=0)
    min_group_rows: int = Field(ge=1)
    passes: int = Field(3, ge=1)  # giving back in one segment can move another; a few passes


class Conservative(BaseModel):
    """Conservative mode by expected value with the risk corrected (ADR-0019)."""

    use_mature_ratio: bool
    review_capacity: float | None = Field(None, gt=0, le=1)  # share of the batch (ADR-0021)
    fairness: FairnessCap | None = None  # ADR-0015

    def capacity(self, rows: int) -> int | None:
        """Review slots of a batch with ``rows`` applications (None = unlimited)."""
        return None if self.review_capacity is None else int(self.review_capacity * rows)


class PolicyConfig(BaseModel):
    """Whole policy file."""

    version: int
    status: str
    dry_run: bool
    kill_switch: bool
    conservative_mode: Literal["auto", "on", "off"]
    cool_down_batches: int = Field(ge=1)
    output_alerts: list[str]
    conservative: Conservative
    manual_review_value: float
    rules: list[Rule]
    actions: dict[ActionCode, str]


def load_policy(path: Path = POLICY_PATH) -> PolicyConfig:
    """Load and validate the policy (read on every batch, so a change applies without deploy)."""
    with path.open(encoding="utf-8") as fh:
        return PolicyConfig.model_validate(yaml.safe_load(fh))
