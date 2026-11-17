"""Retention: expired files are found by age and deleted only with --apply."""

import os
import time

from src.config import PROJECT_ROOT
from src.governance.retention import Item, expired, load_retention, purge
from src.response.guardrails import REASONS

DAY = 86400


def _touch(path, age_days: float, now: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (now - age_days * DAY, now - age_days * DAY))


def test_expired_files_by_age(tmp_path) -> None:
    now = time.time()
    _touch(tmp_path / "b1" / "rows.parquet", 120, now)
    _touch(tmp_path / "b2" / "rows.parquet", 10, now)
    assert [p.parent.name for p in expired(tmp_path, 90, now)] == ["b1"]
    assert expired(tmp_path / "missing", 90, now) == []


def test_purge_is_a_dry_run_unless_applied(tmp_path) -> None:
    now = time.time()
    old = tmp_path / "old.jsonl"
    _touch(old, 400, now)
    item = Item(id="RET-99", data="t", period="1 ano", basis="t", mechanism="t", path="logs",
                days=365)  # fmt: skip
    assert purge(item, tmp_path, now, apply=False) == 1 and old.exists()
    assert purge(item, tmp_path, now, apply=True) == 1 and not old.exists()


def test_every_purged_item_has_path_and_days() -> None:
    items = load_retention().items
    assert all((i.path is None) == (i.days is None) for i in items)
    assert {i.id for i in items if i.path} == {"RET-04", "RET-05"}


def test_governance_plan_lists_every_retention_item_and_reason_code() -> None:
    doc = (PROJECT_ROOT / "docs" / "GOVERNANCE.md").read_text(encoding="utf-8")
    missing = [i.id for i in load_retention().items if f"| {i.id} |" not in doc]
    missing += [code for code in REASONS if f"| {code} |" not in doc]
    assert not missing, f"missing in GOVERNANCE.md: {missing}"
