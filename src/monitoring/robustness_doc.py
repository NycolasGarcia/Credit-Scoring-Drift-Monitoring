"""``docs/ROBUSTNESS.md`` and the RUN record of the robustness study (generated, not edited)."""

import json
from typing import Any

from src.config import PROJECT_ROOT
from src.reporting.run_record import RunRecord

DOC = PROJECT_ROOT / "docs" / "ROBUSTNESS.md"
NOTES = PROJECT_ROOT / "docs" / "robustness_notes.md"
EVIDENCE = PROJECT_ROOT / "docs" / "evidence" / "drift" / "robustness.json"
OK = {True: "ok", False: "**não**", None: "—"}


def _pct(v: float) -> str:
    return f"{100 * v:.0f}%"


def _ci(cell: dict[str, Any]) -> str:
    ci = cell["diagnosis_ci"]
    if ci is None:
        return "—"
    k, n = cell["diagnosis_correct"], cell["diagnosis_alerting"]
    return f"{k}/{n} ({_pct(k / n)}; IC {_pct(ci[0])} a {_pct(ci[1])})"


def _m(v: float) -> str:
    return "—" if v == 0 else f"{v:g}".replace(".", ",")


def detection_rows(cells: list[dict[str, Any]]) -> list[str]:
    """Detection table, one row per (scenario, m)."""
    head = (
        "| Cenário | m | Detectadas em SEV-2+ | Em SEV-1+ | Atraso mediano (SEV-2) | "
        "Diagnóstico certo nos lotes alertados | Falso alarme antes do início (SEV-1 / "
        "SEV-2) | Detecção | Diagnóstico | Falso alarme |\n"
        "|---|---|---|---|---|---|---|---|---|---|"
    )
    rows = [head]
    for c in cells:
        v, d = c["verdict"], c["median_delay"]
        fa = f"{c['pre_sev1']}/{c['pre_batches']} · {c['pre_sev2']}/{c['pre_batches']}"
        rows.append(
            f"| {c['scenario']} | {_m(c['m'])} | {c['detected']}/{c['seeds']} | "
            f"{c['sev1_detected']}/{c['seeds']} | {'—' if d is None else f'{d:g}'} | "
            f"{_ci(c)} | {fa} | {OK[v['detection']] if c['m'] else '—'} | "
            f"{OK[v['diagnosis']]} | {OK[v['false_alarm']]} |"
        )
    return rows


def _k(v: float) -> str:
    return f"{v / 1000:,.0f}".replace(",", ".")


def response_rows(summary: list[dict[str, Any]]) -> list[str]:
    """Response table: delta vs. doing nothing over the seeds, in US$ thousand."""
    rows = [
        "| Cenário | Estratégia | Mediana (US$ mil) | Mín. | Máx. | Seeds com ganho | Robusta |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in summary:
        rows.append(
            f"| {r['scenario']} | {r['strategy']} | {_k(r['median'])} | {_k(r['min'])} | "
            f"{_k(r['max'])} | {r['positive']}/{r['seeds']} | {OK[r['robust']]} |"
        )
    return rows


def gate_line(responses: list[dict[str, Any]]) -> str:
    """How often the challenger passed the gate, per scenario."""
    parts = []
    for sid in sorted({r["scenario"] for r in responses}):
        sub = [r for r in responses if r["scenario"] == sid and r["decision_point"] is not None]
        parts.append(f"{sid} {sum(r['gate_passed'] for r in sub)}/{len(sub)}")
    return "Gate do challenger aprovado no ponto de decisão: " + ", ".join(parts) + "."


def render(body: dict[str, Any]) -> str:
    """Whole document."""
    c, r = body["config"], body["config"]["reading"]
    lines = [
        "# Robustez do detector e das respostas\n",
        "> Gerado por `make robustness` (`src/monitoring/robustness_doc.py`). Não editar à mão.\n",
        f"RUN: [{body['run_id']}](runs/{body['run_id']}.md). Seeds {c['seeds']} (nunca usadas "
        f"antes); magnitudes m = {c['magnitudes']} vezes a intensidade oficial; controle "
        f"{c['control']} variado só em seed. Regra de leitura declarada antes da execução em "
        "`config/monitoring/robustness.yaml`: detecção robusta se ≥ "
        f"{_pct(r['min_detection_share'])} das seeds chegam a SEV-{r['detected_level']}+; "
        "diagnóstico robusto se o limite inferior do intervalo de Wilson (95%) da acurácia "
        f"for ≥ {_pct(r['min_diagnosis_lower'])}; nenhum lote em SEV-2+ antes do início do "
        "drift. O intervalo trata os lotes como independentes, o que o deixa otimista.\n",
        "## Detecção e diagnóstico\n",
        *detection_rows(body["cells"]),
        "\n## Respostas na magnitude oficial\n",
        "Diferença de valor contra não fazer nada, com a revisão tratada como perda, por seed.\n",
        gate_line(body["responses"]) + "\n",
        *response_rows(body["response_summary"]),
    ]
    if NOTES.exists():
        lines += ["", NOTES.read_text(encoding="utf-8").rstrip()]
    return "\n".join(lines) + "\n"


def write_doc(body: dict[str, Any]) -> None:
    """Write docs/ROBUSTNESS.md."""
    DOC.write_text(render(body), encoding="utf-8", newline="\n")


def robustness_record(body: dict[str, Any], run_id: str, git: tuple[str, bool]) -> RunRecord:
    """RUN record (kind ``calib``) of the robustness study."""
    metrics = {
        f"{c['scenario']} m={_m(c['m'])}": {
            "detectadas SEV-2+": f"{c['detected']}/{c['seeds']}",
            "diagnóstico certo": f"{c['diagnosis_correct']}/{c['diagnosis_alerting']}",
            "SEV-2 antes do início": f"{c['pre_sev2']}/{c['pre_batches']}",
        }
        for c in body["cells"]
    }
    m0 = body["config"]["compare_magnitude"]
    fails = [
        f"{c['scenario']} m={_m(c['m'])}"
        for c in body["cells"]
        if False in c["verdict"].values() and (c["m"] in (0.0, m0))
    ]
    verdict = (
        "magnitude oficial e controle dentro da regra declarada"
        if not fails
        else "fora da regra na magnitude oficial ou no controle: " + ", ".join(fails)
    )
    return RunRecord(
        run_id=run_id,
        kind="calib",
        scenario="ROBUST",
        seed=0,
        data_hash=body["thresholds"],
        model="champion",
        mlflow_ref="—",
        metrics=metrics,
        verdict=verdict,
        sha=git[0],
        dirty=git[1],
        artifacts=["docs/evidence/drift/robustness.json", "docs/ROBUSTNESS.md"],
        extra={
            "seeds": str(body["config"]["seeds"]),
            "magnitudes": str(body["config"]["magnitudes"]),
        },
    )


def main() -> None:
    """Regenerate the document from the committed evidence (after editing the notes)."""
    write_doc(json.loads(EVIDENCE.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
