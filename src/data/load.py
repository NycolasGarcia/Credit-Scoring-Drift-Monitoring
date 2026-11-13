"""Raw dataset loader.

Reads only the columns the project is allowed to use (inventory-driven), with explicit
types, and normalizes them into analysis-ready dtypes. Free text, discarded and
post-origination columns are never loaded, except ``last_pymnt_d`` which only dates
the snapshot and is dropped right after.
"""

import hashlib
import logging
from pathlib import Path

import pandas as pd
import pyarrow as pa
from pyarrow import csv as pacsv

from src.data.features import CATEGORICAL_FEATURES, raw_feature_columns
from src.data.inventory import load_inventory

logger = logging.getLogger(__name__)

STRING_COLUMNS = ("id", "loan_status", "issue_d", "application_type", "addr_state",
                  "earliest_cr_line", "last_pymnt_d", "term", "emp_length",
                  *CATEGORICAL_FEATURES)  # fmt: skip
DATE_FORMAT = "%b-%Y"
SNAPSHOT_COLUMN = "last_pymnt_d"


def columns_to_load() -> list[str]:
    """Key, target, metadata, segment and feature columns, plus snapshot/derivation inputs."""
    inv = load_inventory()
    keep = [*inv.by_use("chave"), *inv.by_use("alvo"), *inv.by_use("metadado"),
            *inv.by_use("segmento"), *raw_feature_columns()]  # fmt: skip
    return [*dict.fromkeys([*keep, "earliest_cr_line", SNAPSHOT_COLUMN])]


def file_sha256(path: Path, chunk: int = 1 << 22) -> str:
    """SHA-256 of a file, streamed."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def read_raw(path: Path) -> pd.DataFrame:
    """Read the allowed columns with explicit types (strings stay strings)."""
    cols = columns_to_load()
    types = {c: pa.float64() for c in cols} | {c: pa.string() for c in STRING_COLUMNS}
    table = pacsv.read_csv(
        path,
        convert_options=pacsv.ConvertOptions(
            include_columns=cols, column_types=types, strings_can_be_null=True
        ),
    )
    return table.to_pandas()


def _parse_emp_length(values: pd.Series) -> pd.Series:
    """'< 1 year' -> 0, '10+ years' -> 10, 'n/a' or missing -> NaN."""
    digits = values.str.replace("< 1", "0", regex=False).str.extract(r"(\d+)")[0]
    return pd.to_numeric(digits, errors="coerce")


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Drop footer rows and convert strings to analysis dtypes."""
    df = raw[raw["issue_d"].notna() & raw["loan_status"].notna()].copy()
    for col in ("issue_d", "earliest_cr_line", SNAPSHOT_COLUMN):
        df[col] = pd.to_datetime(df[col], format=DATE_FORMAT, errors="coerce")
    df["term"] = pd.to_numeric(df["term"].str.extract(r"(\d+)")[0], errors="coerce")
    df["emp_length"] = _parse_emp_length(df["emp_length"])
    logger.info("raw normalized", extra={"rows_in": len(raw), "rows_out": len(df)})
    return df


def load_dataset(path: Path) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Load, normalize and return the frame plus the data snapshot date.

    The snapshot is the latest payment month observed; the column is then dropped.
    """
    df = normalize(read_raw(path))
    snapshot = df[SNAPSHOT_COLUMN].max()
    return df.drop(columns=[SNAPSHOT_COLUMN]), snapshot
