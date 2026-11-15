"""Alerting: level per source, catalog completeness, generated rules and docs in sync."""

import re

import pytest
import yaml

from src.alerting import rules
from src.alerting.engine import BatchFacts, active, alert_levels
from src.alerting.settings import load_alert_config
from src.config import PROJECT_ROOT
from src.monitoring.settings import load_monitoring_config
from src.observability import dashboard, metrics

CFG = load_alert_config()
QUIET = {"feature_psi": 0, "score_psi": 0, "approval_delta_pp": 0, "bad_rate_ratio": 0,
         "auc_drop": 0}  # fmt: skip


def levels(**kw) -> dict[str, int]:
    return alert_levels(BatchFacts(**{"signals": QUIET, "gate_status": "passed", **kw}), CFG)


def test_quiet_batch_fires_nothing() -> None:
    assert active(levels()) == {}


def test_signal_alerts_reuse_detector_severity() -> None:
    out = levels(signals={**QUIET, "bad_rate_ratio": 2, "feature_psi": 1})
    assert out["CDM_BAD_RATE_RATIO"] == 2 and out["CDM_FEATURE_DRIFT"] == 1


@pytest.mark.parametrize(("facts", "alert", "level"), [
    ({"gate_status": "blocked", "blocked_streak": 1}, "CDM_CONTRACT_BLOCKED", 2),
    ({"gate_status": "blocked", "blocked_streak": 2}, "CDM_CONTRACT_BLOCKED", 3),
    ({"soft_triggered": 1}, "CDM_SOFT_RULES", 1),
    ({"unit_bugs": {"annual_inc": {}}}, "CDM_UNIT_BUG_SUSPECTED", 2),
    ({"failed_steps": ["detect"]}, "CDM_STEP_FAILED", 2),
    ({"duration_s": 5.0, "median_duration_s": 2.0}, "CDM_PIPELINE_SLOW", 1),
    ({"duration_s": 3.0, "median_duration_s": 2.0}, "CDM_PIPELINE_SLOW", 0),
])  # fmt: skip
def test_operational_alert_levels(facts: dict, alert: str, level: int) -> None:
    assert levels(**facts)[alert] == level


def test_staleness_is_prometheus_only() -> None:
    assert "CDM_MONITOR_STALE" not in levels()


def test_every_detector_signal_has_an_alert() -> None:
    signals = {a.signal for a in CFG.alerts if a.source == "signal"}
    thresholds = {t.signal for t in load_monitoring_config().thresholds} - {"segment_gap"}
    assert signals == thresholds


def test_every_alert_has_a_playbook_in_the_runbook() -> None:
    runbook = (PROJECT_ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")
    headings = {h.strip().lower() for h in re.findall(r"^### (CDM_[A-Z0-9_]+)", runbook, re.M)}
    assert {a.anchor for a in CFG.alerts} <= headings


def test_generated_rules_and_docs_are_in_sync() -> None:
    assert rules.RULES_PATH.read_text(encoding="utf-8") == rules.render_rules(CFG)
    expected_tests = rules.HEADER + yaml.safe_dump(rules.rule_tests(CFG), sort_keys=False,
                                                   allow_unicode=True)  # fmt: skip
    assert rules.TESTS_PATH.read_text(encoding="utf-8") == expected_tests
    assert rules.ALERTS_DOC.read_text(encoding="utf-8") == rules.render_doc(CFG)
    assert metrics.METRICS_DOC.read_text(encoding="utf-8") == metrics.render_doc()
    assert dashboard.DASHBOARD_PATH.read_text(encoding="utf-8") == dashboard.render()


def test_rules_and_dashboard_only_use_cataloged_metrics() -> None:
    exprs = [r["expr"] for r in rules.prometheus_rules(CFG)["groups"][0]["rules"]]
    exprs += [t["expr"] for p in dashboard.dashboard()["panels"] for t in p["targets"]]
    used = set(re.findall(r"\b(cdm_[a-z_]+)\b", " ".join(exprs)))
    assert used and used <= set(metrics.BY_NAME)


def test_no_threshold_value_is_written_in_promql() -> None:
    exprs = [r["expr"] for r in rules.prometheus_rules(CFG)["groups"][0]["rules"]]
    signal_exprs = [e for e in exprs if "cdm_alert_level" in e]
    assert all(e.endswith(">= 1") for e in signal_exprs)
