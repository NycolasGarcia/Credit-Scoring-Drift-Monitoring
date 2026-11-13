"""Validated data-contract configuration (``config/contracts/contract.yaml``)."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from src.config import PROJECT_ROOT

CONTRACT_PATH = PROJECT_ROOT / "config" / "contracts" / "contract.yaml"


class Band(BaseModel):
    """Inclusive numeric band."""

    min: float
    max: float


class RatioBand(BaseModel):
    """Allowed ratio of a batch statistic to its reference value."""

    min_ratio: float = Field(gt=0)
    max_ratio: float = Field(gt=0)


class DateWindow(BaseModel):
    """Valid issue date window (ISO dates)."""

    min: str
    max: str


class BatchRules(BaseModel):
    """Batch-scope parameters."""

    max_row_failure_rate: float = Field(ge=0, lt=1)
    income_scale: RatioBand
    issue_date_window: DateWindow


class InputRules(BaseModel):
    """Input contract parameters."""

    required: list[str]
    integer_columns: list[str] = Field(default_factory=list)
    ranges: dict[str, tuple[float, float]]
    non_negative: list[str]
    domains: dict[str, list]
    installment_tolerance: float = Field(gt=0)
    sentinels: dict[str, list[float]]


class SoftRules(BaseModel):
    """Warning-only parameters."""

    null_rate_tolerance: float = Field(gt=0)
    volume: Band
    utilization_ceiling: float
    extreme_tail_max_share: float = Field(gt=0, lt=1)


class OutputRules(BaseModel):
    """Scored-batch contract parameters."""

    decisions: list[str]


class ContractConfig(BaseModel):
    """Whole contract configuration."""

    version: int
    batch: BatchRules
    input: InputRules
    soft: SoftRules
    output: OutputRules


@lru_cache(maxsize=1)
def load_contract_config(path: Path = CONTRACT_PATH) -> ContractConfig:
    """Load and validate the contract YAML."""
    with path.open(encoding="utf-8") as fh:
        return ContractConfig.model_validate(yaml.safe_load(fh))
