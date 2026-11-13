"""``make drift-docs``: render THRESHOLDS.md and DRIFT_EVALUATION.md from config and evidence."""

import json
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT
from src.monitoring.settings import MonitoringConfig, load_monitoring_config

DOCS = PROJECT_ROOT / "docs"
EVIDENCE = DOCS / "evidence" / "drift"
THRESHOLDS_DOC = DOCS / "THRESHOLDS.md"
EVALUATION_DOC = DOCS / "DRIFT_EVALUATION.md"
NOTES = {THRESHOLDS_DOC: DOCS / "thresholds_notes.md", EVALUATION_DOC: DOCS / "drift_notes.md"}
HEADER = "> Gerado por `make drift-docs` (`src/monitoring/docs.py`). Não editar à mão.\n"
CURRENT_HEAD = (
    "| Id | Sinal | Camada | Direção | SEV-1 | SEV-2 | SEV-3 | Status | RUN |\n"
    "|---|---|---|---|---|---|---|---|---|"
)
CALIB_HEAD = (
    "| Sinal | Mediana nula | q95 | q99 | Máx. nulo | SEV-1 proposto | FA no proposto "
    "| SEV-1 calibrado | SEV-2 calibrado |\n|---|---|---|---|---|---|---|---|---|"
)
SUMMARY_HEAD = (
    "| Cenário | RUN | Diagnóstico certo | 1º SEV-1 (atraso) | 1º SEV-2 (atraso) | Camadas "
    "esperadas | Camadas acionadas | Atribuição recall / precisão | Acurácia do diagnóstico "
    "| Falso alarme |\n|---|---|---|---|---|---|---|---|---|---|"
)
EVIDENTLY_INTRO = (
    "Janela escolhida pelo detector (do 1º alerta em diante; últimos lotes se nada alertou). "
    "Teste por coluna: `psi_ref` (PSI com bins da referência, registrado no Evidently), limiar "
    "{sev1}. Última coluna: diferença máxima para o PSI próprio nas colunas sem nulos.\n"
)
EVIDENTLY_HEAD = (
    "| Cenário | HTML | Linhas | Colunas acima do limiar | Máx. dif. (sem nulos) |\n"
    "|---|---|---|---|---|"
)
KS_HEAD = (
    "| Cenário | Pares lote-feature | KS p < 0,05 | PSI ≥ SEV-1 | KS rejeita com PSI abaixo de "
    "SEV-1 |\n|---|---|---|---|---|"
)
EVALUATION_INTRO = (
    "Cada cenário tem ground truth conhecido ([SCENARIOS.md](SCENARIOS.md)); o detector é "
    "avaliado como um classificador (§8.8). Atraso em lotes após o início do drift; falso alarme "
    "medido nos lotes sem drift (S0 inteiro, ou antes do início).\n"
)


def _f(v: Any, nd: int = 3) -> str:
    if v is None:
        return "—"
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def _pct(v: Any) -> str:
    return "—" if v is None else f"{100 * v:.0f}%"


def _load(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _notes(doc: Path) -> list[str]:
    note = NOTES[doc]
    return ["", note.read_text(encoding="utf-8").rstrip()] if note.exists() else []


def _run_link(run: str | None) -> str:
    return f"[{run}](runs/{run}.md)" if run else "—"


def _current_rows(cfg: MonitoringConfig) -> list[str]:
    rows = [CURRENT_HEAD]
    for t in cfg.thresholds:
        sev3 = f"≥ {t.sev3_min_features} top-k" if t.sev3_min_features else _f(t.sev3)
        rows.append(
            f"| {t.id} | `{t.signal}` | {t.layer} | {t.direction} | {_f(t.sev1)} | "
            f"{_f(t.sev2)} | {sev3} | {t.status} | {_run_link(t.calibration_run)} |"
        )
    return rows


def _calibration_rows(calib: dict[str, Any]) -> list[str]:
    rows = [
        f"RUN: {_run_link(calib['run_id'])} · {calib['replicates']} réplicas A/A de "
        f"{calib['batch_size']} propostas sorteadas do holdout.\n",
        CALIB_HEAD,
    ]
    for s, c in calib["signals"].items():
        rows.append(
            f"| `{s}` | {_f(c['q50'], 4)} | {_f(c['q95'], 4)} | {_f(c['q99'], 4)} | "
            f"{_f(c['max'], 4)} | {_f(c['proposed']['sev1'])} | "
            f"{_pct(c['fa_proposed_sev1'])} | {_f(c['sev1'])} | {_f(c.get('sev2'))} |"
        )
    prop, cal = calib["false_alarm"]["proposed"], calib["false_alarm"]["calibrated"]
    rows.append(
        f"\nFalso alarme composto (qualquer sinal): SEV-1+ {_pct(prop['sev1_plus'])} com os "
        f"valores propostos → {_pct(cal['sev1_plus'])} calibrado; SEV-2+ "
        f"{_pct(cal['sev2_plus'])}."
    )
    return rows


def _d6_text(cfg: MonitoringConfig) -> str:
    d = cfg.diagnosis
    return (
        f"Cauda abaixo do percentil {100 * d.tail_quantile:g} da referência; suspeita quando o "
        f"excesso na cauda passa de {_pct(d.min_tail_excess)}; confirmada quando corrigir a "
        f"cauda por um fator em {d.unit_factors} reduz o PSI a no máximo "
        f"{_pct(d.max_psi_ratio)} do original ({d.status})."
    )


def render_thresholds(cfg: MonitoringConfig, calib: dict[str, Any] | None) -> str:
    """THRESHOLDS.md body."""
    fa = cfg.false_alarm_target
    intro = (
        f"Fonte: `config/monitoring/thresholds.yaml` (versão {cfg.version}) e "
        "`docs/evidence/drift/calibration_S0.json`. Meta de falso alarme por lote no controle: "
        f"SEV-1+ ≤ {_pct(fa.sev1)}, SEV-2+ ≤ {_pct(fa.sev2)} ({fa.status}). Feature importante "
        f"= top-{cfg.top_k_features} da importância por permutação.\n"
    )
    calib_rows = _calibration_rows(calib) if calib else ["<pendente — `make calibrate`>"]
    lines = [
        "# Limiares do monitoramento\n", HEADER, intro, "## Limiares vigentes\n",
        *_current_rows(cfg), "\n## Calibração no controle (S0)\n", *calib_rows,
        "\n## Racional\n", *[f"- **{t.id}** — {t.rationale}" for t in cfg.thresholds],
        "\n## Assinatura de bug de unidade (D6)\n", _d6_text(cfg), *_notes(THRESHOLDS_DOC),
    ]  # fmt: skip
    return "\n".join(lines) + "\n"


def _scenario_row(sid: str, ev: dict[str, Any]) -> str:
    e = ev["evaluation"]
    att, diag, fa = e["attribution"], e["diagnosis"], e["false_alarm"]
    return (
        f"| {sid} | {_run_link(ev['run_id'])} | {diag['expected']} | "
        f"{_f(e['first_sev1'])} ({_f(e['delay_sev1'])}) | "
        f"{_f(e['first_sev2'])} ({_f(e['delay_sev2'])}) | "
        f"{'/'.join(e['layers_expected']) or '—'} | {'/'.join(e['layers_fired']) or '—'} | "
        f"{_pct(att['recall'])} / {_pct(att['precision'])} | {_pct(diag['accuracy'])} | "
        f"{_pct(fa['sev1_plus']) if fa['batches'] else '—'} |"
    )


def _evidently_row(sid: str, ev: dict[str, Any]) -> str:
    r = ev["evidently"]
    exact = [c["abs_diff"] for c in r["cross_check"]
             if c["null_share"] == 0 and c["column"] != "score"]  # fmt: skip
    return (
        f"| {sid} | [{r['html']}](evidence/drift/{r['html']}) | {r['rows_current']} | "
        f"{', '.join(r['drifted_columns']) or '—'} | {_f(max(exact, default=None), 6)} |"
    )


def _ks_row(sid: str, ev: dict[str, Any], sev1: float) -> str:
    pairs = [(p, b["psi"][f]) for b in ev["batches"] for f, p in b["ks_p"].items()]
    n = max(len(pairs), 1)
    ks = sum(p < 0.05 for p, _ in pairs) / n
    psi = sum(v >= sev1 for _, v in pairs) / n
    both = sum(p < 0.05 and v < sev1 for p, v in pairs) / n
    return f"| {sid} | {len(pairs)} | {_pct(ks)} | {_pct(psi)} | {_pct(both)} |"


def render_evaluation(evs: dict[str, dict[str, Any]], cfg: MonitoringConfig) -> str:
    """DRIFT_EVALUATION.md body."""
    sev1 = cfg.get("feature_psi").sev1
    lines = [
        "# Avaliação do detector de drift\n", HEADER, EVALUATION_INTRO,
        "## Resumo por cenário\n", SUMMARY_HEAD, *[_scenario_row(s, e) for s, e in evs.items()],
        "\n## Relatórios Evidently\n", EVIDENTLY_INTRO.format(sev1=sev1), EVIDENTLY_HEAD,
        *[_evidently_row(s, e) for s, e in evs.items()],
        "\n## p-valor versus tamanho de efeito (NV-10)\n", KS_HEAD,
        *[_ks_row(s, e, sev1) for s, e in evs.items()], *_notes(EVALUATION_DOC),
    ]  # fmt: skip
    return "\n".join(lines) + "\n"


def evidence_by_scenario() -> dict[str, dict[str, Any]]:
    """Detection evidence files present, by scenario id."""
    return {p.stem: _load(p) for p in sorted(EVIDENCE.glob("S[0-9].json"))}


def main() -> None:
    """Write both documents."""
    cfg = load_monitoring_config()
    calib = _load(EVIDENCE / "calibration_S0.json")
    THRESHOLDS_DOC.write_text(render_thresholds(cfg, calib), encoding="utf-8")
    EVALUATION_DOC.write_text(render_evaluation(evidence_by_scenario(), cfg), encoding="utf-8")


if __name__ == "__main__":
    main()
