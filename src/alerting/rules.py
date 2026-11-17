"""``make alerts``: Prometheus rules and docs/ALERTS.md generated from the alert catalog."""

from typing import Any

import yaml

from src.alerting.settings import Alert, AlertConfig, load_alert_config
from src.config import PROJECT_ROOT

RULES_PATH = PROJECT_ROOT / "monitoring" / "rules" / "cdm_alerts.yml"
TESTS_PATH = PROJECT_ROOT / "monitoring" / "rules-tests" / "cdm_alerts_test.yml"
ALERTS_DOC = PROJECT_ROOT / "docs" / "ALERTS.md"
HEADER = "# Gerado por `make alerts` (src/alerting/rules.py) a partir de alerts.yaml. Não editar.\n"
STATIC = {"gate": "SEV-2 · SEV-3 com 2 lotes bloqueados seguidos", "soft_rules": "SEV-1",
          "unit_bug": "SEV-2", "step_failed": "SEV-2", "slow": "SEV-1",
          "staleness": "SEV-3",
          "fairness": "SEV-1 se o gap cresce > 3 p.p.; SEV-2 se > 7 p.p. "
                      "(`config/governance/fairness.yaml`)"}  # fmt: skip


def _annotations(alert: Alert, cfg: AlertConfig) -> dict[str, str]:
    return {"summary": alert.title, "diagnosis": alert.diagnosis, "action": alert.action,
            "owner": cfg.owner, "playbook": f"{cfg.runbook}#{alert.anchor}"}  # fmt: skip


def _rule(alert: Alert, cfg: AlertConfig) -> dict[str, Any]:
    if alert.source == "staleness":  # one monitor, many data streams: any success keeps it quiet
        expr = ("time() - max(cdm_last_success_timestamp_seconds) > "
                f"{cfg.staleness.limit_seconds:g}")  # fmt: skip
        severity = "SEV-3"
    else:
        expr = f'max by (scenario) (cdm_alert_level{{alert="{alert.id}"}}) >= 1'
        severity = "SEV-{{ $value }}"
    return {"alert": alert.id, "expr": expr,
            "labels": {"severity": severity, "layer": alert.layer},
            "annotations": _annotations(alert, cfg)}  # fmt: skip


def prometheus_rules(cfg: AlertConfig) -> dict[str, Any]:
    """Rule file body: one rule per alert."""
    return {"groups": [{"name": "cdm_alerts", "rules": [_rule(a, cfg) for a in cfg.alerts]}]}


def render_rules(cfg: AlertConfig) -> str:
    """Rules file text."""
    return HEADER + yaml.safe_dump(prometheus_rules(cfg), sort_keys=False, allow_unicode=True)


def _severity(alert: Alert) -> str:
    if alert.source == "signal":
        return f"SEV-1 a 3 conforme [`{alert.signal}`](THRESHOLDS.md)"
    return STATIC[alert.source]


def render_doc(cfg: AlertConfig) -> str:
    """docs/ALERTS.md body."""
    rows = [f"| `{a.id}` | {a.title} | {a.layer} | {_severity(a)} | {a.diagnosis} | {a.action} | "
            f"[playbook](RUNBOOK.md#{a.anchor}) |" for a in cfg.alerts]  # fmt: skip
    return "\n".join([
        "# Catálogo de alertas\n",
        "> Gerado por `make alerts` (`src/alerting/rules.py`) a partir de "
        "`config/monitoring/alerts.yaml`. Não editar à mão.\n",
        "Os cortes dos sinais estão em [THRESHOLDS.md](THRESHOLDS.md); as regras do Prometheus, "
        "em `monitoring/rules/cdm_alerts.yml`. Decisões: "
        "[ADR-0011](adr/0011-severity-alert-policy.md).",
        f"Dono de todos os alertas: {cfg.owner}. Dead man's switch: dispara após "
        f"{cfg.staleness.limit_seconds:g} s sem lote concluído com sucesso.\n",
        "| Id | Alerta | Camada | Severidade | Diagnóstico | Ação (§8.5) | Playbook |",
        "|---|---|---|---|---|---|---|", *rows,
    ]) + "\n"  # fmt: skip


def _expected(alert: Alert, cfg: AlertConfig, severity: str) -> list[dict[str, Any]]:
    labels = {"severity": severity, "layer": alert.layer}
    if alert.source != "staleness":
        labels["scenario"] = "S9"
    return [{"exp_labels": labels, "exp_annotations": _annotations(alert, cfg)}]


def _still_running(cfg: AlertConfig, step: int, limit: int) -> dict[str, Any]:
    """Second test: another scenario keeps succeeding, so the monitor is not stale."""
    stale = next(a for a in cfg.alerts if a.source == "staleness")
    n = (limit // step) + 10
    series = [{"series": 'cdm_last_success_timestamp_seconds{scenario="S9"}',
               "values": f"0+{step}x4 20x{n}"},
              {"series": 'cdm_last_success_timestamp_seconds{scenario="S8"}',
               "values": f"0+{step}x{n + 4}"}]  # fmt: skip
    check = {"eval_time": f"{20 + limit + step}s", "alertname": stale.id, "exp_alerts": []}
    return {"interval": f"{step}s", "input_series": series, "alert_rule_test": [check]}


def rule_tests(cfg: AlertConfig) -> dict[str, Any]:
    """promtool unit tests: a signal alert at SEV-2, a quiet signal, the dead man's switch."""
    sig = next(a for a in cfg.alerts if a.source == "signal")
    quiet = next(a for a in cfg.alerts if a.source == "signal" and a.id != sig.id)
    stale = next(a for a in cfg.alerts if a.source == "staleness")
    step, limit = 5, int(cfg.staleness.limit_seconds)
    last = f"0+{step}x4 20x{(limit // step) + 6}"  # success every 5 s until t=20 s, then silence
    level = 'cdm_alert_level{{alert="{}",scenario="S9"}}'
    series = [{"series": level.format(sig.id), "values": "0 0 2 2"},
              {"series": level.format(quiet.id), "values": "0 0 0 0"},
              {"series": 'cdm_last_success_timestamp_seconds{scenario="S9"}',
               "values": last}]  # fmt: skip
    checks = [{"eval_time": "5s", "alertname": sig.id, "exp_alerts": []},
              {"eval_time": "10s", "alertname": sig.id, "exp_alerts": _expected(sig, cfg, "SEV-2")},
              {"eval_time": "15s", "alertname": quiet.id, "exp_alerts": []},
              {"eval_time": f"{20 + limit - step}s", "alertname": stale.id, "exp_alerts": []},
              {"eval_time": f"{20 + limit + step}s", "alertname": stale.id,
               "exp_alerts": _expected(stale, cfg, "SEV-3")}]  # fmt: skip
    return {
        "rule_files": ["../rules/cdm_alerts.yml"],
        "evaluation_interval": f"{step}s",
        "tests": [
            {"interval": f"{step}s", "input_series": series, "alert_rule_test": checks},
            _still_running(cfg, step, limit),
        ],
    }


def main() -> None:
    """Write the rules file, their promtool tests and the alert catalog."""
    cfg = load_alert_config()
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULES_PATH.write_text(render_rules(cfg), encoding="utf-8", newline="\n")
    TESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TESTS_PATH.write_text(
        HEADER + yaml.safe_dump(rule_tests(cfg), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )
    ALERTS_DOC.write_text(render_doc(cfg), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
