"""Structured step events and per-run log files (RO-13, GR-10).

Every step of every batch emits one JSON event with the same fields, whether it succeeded,
failed or was skipped. The run log file uses the same privacy filter as the console.
"""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.logging_config import JsonFormatter, PrivacyFilter

logger = logging.getLogger("cdm.pipeline")
STEPS = ("ingest", "validate", "score", "detect", "evaluate", "alert", "respond", "record")


@dataclass
class StepLog:
    """Events of one batch, in step order."""

    run_id: str
    batch_id: str
    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, step: str, status: str, duration_ms: float, **rows: Any) -> None:
        """Record and log one step event."""
        event = {"run_id": self.run_id, "batch_id": self.batch_id, "step": step,
                 "status": status, "duration_ms": round(duration_ms, 1),
                 "rows_in": rows.get("rows_in"), "rows_out": rows.get("rows_out"),
                 "rows_quarantined": rows.get("rows_quarantined")}  # fmt: skip
        self.events.append(event)
        level = logging.ERROR if status == "failed" else logging.INFO
        logger.log(level, "pipeline step", extra=event)

    @contextmanager
    def step(self, name: str) -> Iterator[dict[str, Any]]:
        """Time a step; the caller fills row counts in the yielded dict. Failures re-raise."""
        rows: dict[str, Any] = {}
        start = time.perf_counter()
        try:
            yield rows
        except Exception:
            self.emit(name, "failed", (time.perf_counter() - start) * 1000, **rows)
            raise
        self.emit(name, "ok", (time.perf_counter() - start) * 1000, **rows)

    def skip(self, name: str) -> None:
        """Record a step that did not run for this batch."""
        self.emit(name, "skipped", 0.0)

    def failed(self) -> list[str]:
        """Steps that failed."""
        return [e["step"] for e in self.events if e["status"] == "failed"]

    def durations_s(self) -> dict[str, float]:
        """Seconds per step."""
        return {e["step"]: e["duration_ms"] / 1000 for e in self.events}


def attach_run_log(path: Path) -> logging.Handler:
    """Also write every log record of this run to ``path`` (JSON lines, privacy filtered)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    handler.addFilter(PrivacyFilter())
    logging.getLogger().addHandler(handler)
    return handler


def detach_run_log(handler: logging.Handler) -> None:
    """Stop writing to the run log file."""
    logging.getLogger().removeHandler(handler)
    handler.close()
