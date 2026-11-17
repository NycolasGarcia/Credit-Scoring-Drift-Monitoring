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


def test_shadow_at_trains_at_the_batch_and_respects_the_limit(monkeypatch) -> None:
    seen = {}
    setup = {"views": "views", "batches": list(range(12))}
    monkeypatch.setattr(gameday.cli, "context", lambda: {"policy": None, "cfg": "cfg", "champ": 1})
    monkeypatch.setattr(gameday.cli, "scenario_setup", lambda sid, policy: setup)
    monkeypatch.setattr(gameday, "challenger_rows", lambda views, t, cfg: seen.update(t=t) or [])
    monkeypatch.setattr(gameday, "train_challenger", lambda rows, cfg: ("ch", None))
    monkeypatch.setattr(gameday.shadow, "shadow_timeline",
                        lambda b, t, champ, ch, ctx: [{"batch": i} for i in b[t + 1:]])  # fmt: skip
    assert [v["batch"] for v in gameday.shadow_at("S2", 8, 10)] == [9]
    assert seen["t"] == 8


def test_shadow_at_reports_a_refused_training(monkeypatch) -> None:
    def refuse(rows, cfg):
        raise gameday.TrainingRefusedError("GR-8: poucos rótulos maduros")

    monkeypatch.setattr(gameday.cli, "context", lambda: {"policy": None, "cfg": "cfg"})
    monkeypatch.setattr(gameday.cli, "scenario_setup", lambda sid, policy: {"views": None})
    monkeypatch.setattr(gameday, "challenger_rows", lambda views, t, cfg: [])
    monkeypatch.setattr(gameday, "train_challenger", refuse)
    assert gameday.shadow_at("S2", 4, 0) == [
        {"batch": 4, "refused": "GR-8: poucos rótulos maduros"}
    ]
