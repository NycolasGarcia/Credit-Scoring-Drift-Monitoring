"""Build the processed partitions from the raw file (``make data``).

raw CSV -> load -> target + maturity -> derived features -> pseudonymize -> partitions
-> parquet per partition + manifest (aggregates and hashes only).
"""

import json
import logging
from pathlib import Path

import pandas as pd

from src.config import PROJECT_ROOT, get_settings
from src.data.features import SEGMENT_COLUMNS, add_derived_features, model_feature_columns
from src.data.load import file_sha256, load_dataset
from src.data.pseudonymize import pseudonymize_ids
from src.data.split import PARTITIONS, assign_partitions, content_hash, load_split_config
from src.data.target import is_mature, map_target
from src.logging_config import configure_logging

logger = logging.getLogger(__name__)

META_COLUMNS = ("loan_key", "issue_d", "vintage", "loan_status", "target", "is_mature")
EVIDENCE_MANIFEST = PROJECT_ROOT / "docs" / "evidence" / "data" / "split_manifest.json"


def build_frame(raw_path: Path, key: str) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Return the full processed frame (all partitions) and the data snapshot."""
    df, snapshot = load_dataset(raw_path)
    df["target"] = map_target(df["loan_status"])
    df["is_mature"] = is_mature(df["issue_d"], df["term"], snapshot)
    df["vintage"] = df["issue_d"].dt.strftime("%Y-%m")
    df = add_derived_features(df)
    df["loan_key"] = pseudonymize_ids(df["id"], key)
    df["partition"] = assign_partitions(df, load_split_config())
    return df.drop(columns=["id"]), snapshot


def partition_summary(part: pd.DataFrame) -> dict:
    """Aggregates describing one partition."""
    labeled = part["target"].notna()
    return {
        "rows": len(part),
        "vintage_min": part["vintage"].min() if len(part) else None,
        "vintage_max": part["vintage"].max() if len(part) else None,
        "labeled_share": round(float(labeled.mean()), 4) if len(part) else None,
        "mature_share": round(float(part["is_mature"].mean()), 4) if len(part) else None,
        "bad_rate_labeled": round(float(part.loc[labeled, "target"].mean()), 4)
        if labeled.any() else None,
        "content_sha256": content_hash(part),
    }  # fmt: skip


def write_partitions(df: pd.DataFrame, out_dir: Path) -> dict[str, dict]:
    """Persist each in-use partition as parquet and return its summary."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cols = [*META_COLUMNS, *model_feature_columns(), *dict.fromkeys(SEGMENT_COLUMNS)]
    cols = [*dict.fromkeys(cols)]
    summaries = {}
    for name in PARTITIONS:
        part = df.loc[df["partition"] == name, cols].reset_index(drop=True)
        if name != "out_of_scope":
            part.to_parquet(out_dir / f"{name}.parquet", index=False)
        summaries[name] = partition_summary(part)
    return summaries


def main() -> None:
    """Entry point: build partitions and write the manifest."""
    settings = get_settings()
    configure_logging(settings.log_level)
    df, snapshot = build_frame(
        settings.raw_data_path, settings.pseudonymization_key.get_secret_value()
    )
    out_dir = settings.data_dir / "processed"
    manifest = {
        "raw_file_sha256": file_sha256(settings.raw_data_path),
        "raw_rows_after_footer_drop": len(df),
        "snapshot": snapshot.strftime("%Y-%m-%d"),
        "split_config": load_split_config().model_dump(),
        "partitions": write_partitions(df, out_dir),
    }
    for path in (out_dir / "split_manifest.json", EVIDENCE_MANIFEST):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("partitions written", extra={"partitions": list(manifest["partitions"])})


if __name__ == "__main__":
    main()
