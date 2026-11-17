"""Game day: the operator view carries no ground truth and the watch stops at the severity."""

from types import SimpleNamespace

from src.observability.events import StepLog
from src.observability.samples import BatchState
from src.response import gameday

KEYS = {
    "batch", "issue_month", "gate", "failed_steps", "alerts", "max_level", "diagnosis",
    "score_psi", "approval_rate", "bad_rate_ratio", "auc_mature", "segment_feature",
    "segment_gap", "rule", "auto", "human", "conservative", "risk_correction", "decisions",
}  # fmt: skip


def _state(index: int, level: int) -> BatchState:
    s = BatchState(index, f"b{index:02d}", "2014-01", StepLog("gd-test", f"b{index:02d}"))
    s.levels = {"CDM_BAD_RATE_RATIO": level, "CDM_SCORE_DRIFT": 0}
    s.l3 = {"score_psi": 0.002, "approval_rate": 0.998}
    s.l4 = {"bad_rate_ratio": 1.27, "auc": 0.71, "segment_feature": "dti", "segment_gap": 0.8}
    s.diagnosis = "D3" if level else "none"
    s.response = {"rule": "P03", "auto": ["A4"], "human": ["A3"], "conservative": True,
                  "risk_correction": 1.27, "decisions": {"approve": 10}}  # fmt: skip
    return s


def test_operator_view_has_only_observable_fields() -> None:
    view = gameday.operator_view(_state(8, 2))
    assert set(view) == KEYS
    assert view["alerts"] == {"CDM_BAD_RATE_RATIO": 2}  # silent alerts are not shown
    assert view["max_level"] == 2


def test_watch_stops_after_first_batch_at_severity(monkeypatch) -> None:
    levels = [0, 1, 2, 2, 3]
    items = [SimpleNamespace(index=i) for i in range(len(levels))]
    monkeypatch.setattr(gameday, "build_context", lambda run_id: None)
    monkeypatch.setattr(gameday, "batch_inputs", lambda scenario, limit: items)
    monkeypatch.setattr(
        gameday, "run_batch", lambda ctx, item, mem: _state(item.index, levels[item.index])
    )
    assert [v["batch"] for v in gameday.watch("S2", "gd-test", 2, 0)] == [0, 1, 2]
    assert len(gameday.watch("S2", "gd-test", 0, 0)) == len(levels)
