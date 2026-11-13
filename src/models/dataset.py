"""Model datasets: internal split of the reference and out-of-time sets."""

import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import get_settings
from src.data.features import model_feature_columns
from src.models.settings import TrainingConfig

TARGET = "target"


def load_partition(name: str) -> pd.DataFrame:
    """Read a processed partition written by ``make data``."""
    path = get_settings().data_dir / "processed" / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run `make data` first")
    return pd.read_parquet(path)


def _strata(df: pd.DataFrame) -> pd.Series:
    return df["vintage"] + "_" + df[TARGET].astype(int).astype(str)


def internal_split(ref: pd.DataFrame, cfg: TrainingConfig) -> dict[str, pd.DataFrame]:
    """Split the reference into train / calibration / test, stratified by vintage x target."""
    held = cfg.internal_split.calibration + cfg.internal_split.test
    train, rest = train_test_split(
        ref, test_size=held, random_state=cfg.seed, stratify=_strata(ref)
    )
    test_share = cfg.internal_split.test / held
    calib, test = train_test_split(
        rest, test_size=test_share, random_state=cfg.seed, stratify=_strata(rest)
    )
    return {"train": train, "calibration": calib, "test": test}


def oot_sets(prod: pd.DataFrame, cfg: TrainingConfig) -> dict[str, pd.DataFrame]:
    """Mature, labeled production loans inside each configured out-of-time window."""
    usable = prod[prod["is_mature"] & prod[TARGET].notna()]
    return {
        name: usable[usable["vintage"].between(start, end)]
        for name, (start, end) in cfg.oot_windows.items()
    }


def xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Model input (allowlist only) and integer target."""
    return df[model_feature_columns()], df[TARGET].astype(int)
