"""Alert engine: batch facts -> level (0-3) of every alert in the catalog.

Signal alerts reuse the severity computed from ``thresholds.yaml``; no cut point lives here.
The dead man's switch is evaluated only by Prometheus (absence cannot be seen from inside).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.alerting.settings import Alert, AlertConfig


@dataclass
class BatchFacts:
    """What the job knows about one batch when it decides the alerts."""

    signals: dict[str, int]
    gate_status: str
    blocked_streak: int = 0
    soft_triggered: int = 0
    unit_bugs: dict[str, Any] = field(default_factory=dict)
    failed_steps: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    median_duration_s: float | None = None


def _signal(alert: Alert, facts: BatchFacts, cfg: AlertConfig) -> int:
    return int(facts.signals.get(alert.signal, 0))


def _gate(alert: Alert, facts: BatchFacts, cfg: AlertConfig) -> int:
    if facts.gate_status != "blocked":
        return 0
    return 3 if facts.blocked_streak >= 2 else 2


def _slow(alert: Alert, facts: BatchFacts, cfg: AlertConfig) -> int:
    median = facts.median_duration_s
    return int(median is not None and facts.duration_s > cfg.slow.duration_multiple * median)


LEVEL: dict[str, Callable[[Alert, BatchFacts, AlertConfig], int]] = {
    "signal": _signal,
    "gate": _gate,
    "soft_rules": lambda a, f, c: int(f.soft_triggered > 0),
    "unit_bug": lambda a, f, c: 2 if f.unit_bugs else 0,
    "step_failed": lambda a, f, c: 2 if f.failed_steps else 0,
    "slow": _slow,
}


def alert_levels(facts: BatchFacts, cfg: AlertConfig) -> dict[str, int]:
    """Level of every in-job alert (the staleness alert is Prometheus-only)."""
    return {a.id: LEVEL[a.source](a, facts, cfg) for a in cfg.alerts if a.source in LEVEL}


def active(levels: dict[str, int]) -> dict[str, str]:
    """Alerts firing in this batch, as ``{id: 'SEV-n'}``."""
    return {k: f"SEV-{v}" for k, v in sorted(levels.items()) if v >= 1}
