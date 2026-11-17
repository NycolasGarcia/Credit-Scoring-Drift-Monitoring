"""``make retention``: purge local data past its retention period (RET items with a path).

Dry run by default: lists how many files of each item are past the period. ``--apply`` deletes
them. Only counts and folders are logged, never file contents (GR-10).
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from src.config import PROJECT_ROOT, get_settings
from src.logging_config import configure_logging

RETENTION_PATH = PROJECT_ROOT / "config" / "governance" / "retention.yaml"
logger = logging.getLogger(__name__)


class Item(BaseModel):
    """One retention rule."""

    id: str = Field(pattern=r"^RET-\d{2}$")
    data: str
    period: str
    basis: str
    mechanism: str
    path: str | None = None
    days: int | None = Field(None, ge=1)


class RetentionConfig(BaseModel):
    """Whole retention file."""

    version: int
    status: str
    items: list[Item]


def load_retention(path: Path = RETENTION_PATH) -> RetentionConfig:
    """Load and validate the retention YAML."""
    with path.open(encoding="utf-8") as fh:
        return RetentionConfig.model_validate(yaml.safe_load(fh))


def expired(root: Path, days: int, now: float) -> list[Path]:
    """Files under ``root`` last modified more than ``days`` ago."""
    if not root.exists():
        return []
    limit = now - days * 86400
    return [p for p in root.rglob("*") if p.is_file() and p.stat().st_mtime < limit]


def resolve(path: str) -> Path:
    """``data/...`` and ``logs`` follow the configured folders (they may live outside the repo)."""
    s = get_settings()
    if path.startswith("data/"):
        return s.data_dir / path.removeprefix("data/")
    return s.logs_dir if path == "logs" else PROJECT_ROOT / path


def purge(item: Item, root: Path, now: float, apply: bool) -> int:
    """Count (and, with ``apply``, delete) the expired files of one item under ``root``."""
    files = expired(root, item.days, now)
    if apply:
        for f in files:
            f.unlink()
    logger.info("retention", extra={"item": item.id, "path": item.path, "days": item.days,
                                    "expired_files": len(files), "applied": apply})  # fmt: skip
    return len(files)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    configure_logging(get_settings().log_level)
    p = argparse.ArgumentParser(description="Purge local data past its retention period.")
    p.add_argument("--apply", action="store_true", help="delete (default: dry run)")
    args, now = p.parse_args(argv), time.time()
    for item in load_retention().items:
        if item.path and item.days:
            purge(item, resolve(item.path), now, args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
