"""Violation report and quarantine store (GR-2).

The report is aggregate-only: rule ids, descriptions, counts, rates and, for new categories,
domain level names. No row values ever enter it (GR-10). Quarantined rows are written to
``data/quarantine/`` (git-ignored, pseudonymized keys only) for reprocessing after a fix.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.contracts.rules import RULES
from src.contracts.settings import ContractConfig
from src.contracts.validate import ContractResult


def build_report(result: ContractResult, batch_id: str, cfg: ContractConfig) -> dict[str, Any]:
    """Aggregate description of a validation outcome."""
    return {
        "batch_id": batch_id,
        "contract_version": cfg.version,
        "validated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": result.status,
        "rows_in": result.rows_in,
        "rows_valid": len(result.valid),
        "rows_quarantined": len(result.quarantined),
        "row_failure_rate": round(result.row_failure_rate, 6),
        "max_row_failure_rate": cfg.batch.max_row_failure_rate,
        "hard_violations": [
            {"rule": r, "scope": RULES[r].scope, "description": RULES[r].description, "count": n}
            for r, n in sorted(result.rule_counts.items())
        ],
        "soft_warnings": {k: v for k, v in result.soft.items() if v.get("triggered")},
    }


def write_quarantine(result: ContractResult, report: dict[str, Any], root: Path) -> Path | None:
    """Persist quarantined rows and the report; returns the folder (None if nothing to keep)."""
    if not len(result.quarantined):
        return None
    folder = root / report["batch_id"]
    folder.mkdir(parents=True, exist_ok=True)
    result.quarantined.to_parquet(folder / "rows.parquet", index=False)
    (folder / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return folder
