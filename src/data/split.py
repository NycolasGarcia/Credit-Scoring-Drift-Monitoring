"""Reference x production separation (ADR-0005).

Partitions:
    reference   -> mature, labeled vintages used for training/validation/test.
    holdout     -> same vintages, never trained on; base of simulated scenarios.
    production  -> later vintages; natural drift, labels only where matured.
    out_of_scope-> joint applications, earlier vintages, unresolved reference loans.
"""

import hashlib
from pathlib import Path

import pandas as pd
import yaml
from pydantic import BaseModel, Field
from sklearn.model_selection import train_test_split

from src.config import PROJECT_ROOT

SPLIT_CONFIG_PATH = PROJECT_ROOT / "config" / "data" / "split.yaml"
PARTITIONS = ("reference", "holdout", "production", "out_of_scope")


class SplitConfig(BaseModel):
    """Validated split parameters."""

    scope_application_type: str
    reference_start: str
    reference_end: str
    production_start: str
    holdout_fraction: float = Field(gt=0, lt=1)
    seed: int


def load_split_config(path: Path = SPLIT_CONFIG_PATH) -> SplitConfig:
    """Load the split YAML."""
    with path.open(encoding="utf-8") as fh:
        return SplitConfig.model_validate(yaml.safe_load(fh))


def _month(value: str) -> pd.Timestamp:
    return pd.Timestamp(f"{value}-01")


def reference_pool_mask(df: pd.DataFrame, cfg: SplitConfig) -> pd.Series:
    """In-scope, reference-window loans that are mature and resolved."""
    in_window = df["issue_d"].between(_month(cfg.reference_start), _month(cfg.reference_end))
    return in_scope_mask(df, cfg) & in_window & df["is_mature"] & df["target"].notna()


def in_scope_mask(df: pd.DataFrame, cfg: SplitConfig) -> pd.Series:
    """Loans of the application type the model is built for."""
    return df["application_type"] == cfg.scope_application_type


def assign_partitions(df: pd.DataFrame, cfg: SplitConfig) -> pd.Series:
    """Label every row with exactly one partition (deterministic for a given seed)."""
    part = pd.Series("out_of_scope", index=df.index, dtype="object")
    pool = df.index[reference_pool_mask(df, cfg)]
    strata = df.loc[pool, "issue_d"].dt.strftime("%Y-%m") + "_" + df.loc[pool, "target"].astype(str)
    ref_idx, hold_idx = train_test_split(
        pool, test_size=cfg.holdout_fraction, random_state=cfg.seed, stratify=strata
    )
    part[ref_idx] = "reference"
    part[hold_idx] = "holdout"
    prod = in_scope_mask(df, cfg) & (df["issue_d"] >= _month(cfg.production_start))
    part[prod] = "production"
    return part


def content_hash(df: pd.DataFrame) -> str:
    """Order-sensitive SHA-256 of the frame content (independent of file format)."""
    hashed = pd.util.hash_pandas_object(df, index=False).to_numpy()
    return hashlib.sha256(hashed.tobytes()).hexdigest()
