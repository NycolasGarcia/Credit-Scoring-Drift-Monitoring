"""Metric catalog and Pushgateway export (ADR-0010). Also renders docs/METRICS.md.

Every gauge is declared once here (name, help, labels, group, dashboard panel). The job
builds samples for one batch and pushes them as the state of the ``scenario`` group.
"""

from dataclasses import dataclass
from typing import Any

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from src.config import PROJECT_ROOT

JOB = "cdm_monitoring"
METRICS_DOC = PROJECT_ROOT / "docs" / "METRICS.md"


@dataclass(frozen=True)
class MetricDef:
    """One exported gauge."""

    name: str
    help: str
    labels: tuple[str, ...]
    group: str
    panel: str


def _m(name: str, help_: str, labels: tuple[str, ...], group: str, panel: str) -> MetricDef:
    return MetricDef(name, help_, labels, group, panel)


CATALOG: tuple[MetricDef, ...] = (
    _m("cdm_batch_index", "Índice do lote no cenário (eixo do replay)", (), "operacional",
       "Lote e mês"),
    _m("cdm_batch_info", "Lote processado (valor 1; mês simulado no rótulo)",
       ("batch_id", "issue_month"), "operacional", "Lote e mês"),
    _m("cdm_step_status", "Etapa do job: 1 concluída, 0 falhou, -1 pulada", ("step",),
       "operacional", "Saúde do pipeline"),
    _m("cdm_step_duration_seconds", "Duração da etapa", ("step",), "operacional",
       "Duração por etapa"),
    _m("cdm_batch_duration_seconds", "Duração total do lote", (), "operacional",
       "Duração por etapa"),
    _m("cdm_batch_rows", "Linhas por estágio: in, valid, quarantined, scored", ("stage",),
       "operacional", "Volume e quarentena"),
    _m("cdm_gate_blocked", "1 se o contrato bloqueou o lote", (), "operacional",
       "Volume e quarentena"),
    _m("cdm_last_success_timestamp_seconds", "Fim do último lote concluído (dead man's switch)",
       (), "operacional", "Saúde do pipeline"),
    _m("cdm_feature_psi", "PSI da feature contra os bins da referência", ("feature",), "dados",
       "PSI por feature e lote"),
    _m("cdm_features_drifted", "Features com PSI acima do SEV-1", (), "dados",
       "PSI por feature e lote"),
    _m("cdm_score_psi", "PSI do score contra os decis da referência", (), "modelo",
       "Score e aprovação"),
    _m("cdm_approval_rate", "Taxa de aprovação do lote", (), "modelo", "Score e aprovação"),
    _m("cdm_expected_bad_rate", "Bad rate esperado (média do score)", (), "modelo",
       "Score e aprovação"),
    _m("cdm_observed_bad_rate", "Bad rate observado nos rótulos que amadurecem", (), "modelo",
       "Desempenho com rótulo maduro"),
    _m("cdm_bad_rate_ratio", "Observado / esperado nos rótulos que amadurecem", (), "modelo",
       "Desempenho com rótulo maduro"),
    _m("cdm_auc_mature", "AUC dos rótulos que amadurecem", (), "modelo",
       "Desempenho com rótulo maduro"),
    _m("cdm_labeled_rows", "Rótulos que amadurecem no lote", (), "modelo",
       "Desempenho com rótulo maduro"),
    _m("cdm_signal_severity", "Severidade por sinal (0-3)", ("signal",), "alertas",
       "Severidade por sinal"),
    _m("cdm_batch_severity", "Severidade do lote (máximo dos sinais)", (), "alertas",
       "Severidade por sinal"),
    _m("cdm_alert_level", "Nível do alerta (0-3), lido pelas regras do Prometheus", ("alert",),
       "alertas", "Alertas"),
    _m("cdm_alerts_firing", "Alertas ativos no lote por severidade", ("severity",), "alertas",
       "Alertas"),
    _m("cdm_diagnosis", "Diagnóstico do lote (valor 1 no código vigente)", ("code",), "alertas",
       "Diagnóstico"),
    _m("cdm_conservative_mode", "1 se o modo conservador (GR-4) está ativo", (), "resposta",
       "Resposta"),
    _m("cdm_risk_correction", "Fator de correção do risco (última razão obs/esp, se > 1)", (),
       "resposta", "Resposta"),
    _m("cdm_expected_bad_rate_approved", "Bad rate esperado dos aprovados com risco corrigido "
       "(acompanha o apetite de 14%)", (), "resposta", "Resposta"),
    _m("cdm_kill_switch", "1 se a decisão automática está suspensa (GR-9)", (), "resposta",
       "Resposta"),
    _m("cdm_policy_rule", "Regra da matriz de resposta aplicada (valor 1)", ("rule",),
       "resposta", "Resposta"),
    _m("cdm_decisions", "Decisões finais do lote: approve, review, reject", ("decision",),
       "resposta", "Resposta"),
    _m("cdm_fairness_gap_pp", "Gap de aprovação entre grupos (p.p.) da política e do champion "
       "puro, por segmento", ("segment", "decision"), "resposta", "Fairness"),
    _m("cdm_fairness_gap_increase_pp", "Aumento do gap de aprovação causado pela política (p.p.)",
       ("segment",), "resposta", "Fairness"),
)  # fmt: skip
BY_NAME = {m.name: m for m in CATALOG}
Sample = tuple[str, dict[str, str], float]


def build_registry(samples: list[Sample]) -> CollectorRegistry:
    """Registry holding the given samples (unknown metric names are an error)."""
    registry = CollectorRegistry()
    gauges = {}
    for name, labels, value in samples:
        m = BY_NAME[name]
        if name not in gauges:
            gauges[name] = Gauge(name, m.help, m.labels, registry=registry)
        g = gauges[name]
        (g.labels(**labels) if m.labels else g).set(value)
    return registry


def push(samples: list[Sample], gateway: str, scenario: str) -> None:
    """Replace the ``scenario`` group on the Pushgateway with this batch's samples."""
    registry = build_registry(samples)
    push_to_gateway(gateway, job=JOB, grouping_key={"scenario": scenario}, registry=registry)


def render_doc() -> str:
    """docs/METRICS.md body."""
    rows = [f"| `{m.name}` | gauge | {', '.join(f'`{x}`' for x in m.labels) or '—'} | "
            f"{m.group} | {m.help} | {m.panel} |" for m in CATALOG]  # fmt: skip
    intro = ("Todas as métricas são gauges publicados pelo job no Pushgateway, no grupo "
             f"`job={JOB}, scenario=<id>`; cada push substitui o estado do lote anterior "
             "([ADR-0010](adr/0010-observability-stack.md)).\n")  # fmt: skip
    return "\n".join(["# Catálogo de métricas\n",
                      "> Gerado por `make alerts` (`src/observability/metrics.py`). Não editar.\n",
                      intro, "| Métrica | Tipo | Rótulos | Grupo | Significado | Painel |",
                      "|---|---|---|---|---|---|", *rows]) + "\n"  # fmt: skip


def metric_names(samples: list[Sample]) -> set[str]:
    """Distinct metric names in a sample list."""
    return {s[0] for s in samples}


def as_dict(samples: list[Sample]) -> dict[str, Any]:
    """Flat ``name{k=v}`` -> value view (used by logs and tests)."""
    return {name + ("{" + ",".join(f"{k}={v}" for k, v in sorted(lb.items())) + "}" if lb else ""):
            value for name, lb, value in samples}  # fmt: skip


def main() -> None:
    """Write docs/METRICS.md."""
    METRICS_DOC.write_text(render_doc(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
