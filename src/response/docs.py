"""RESPONSE_EVALUATION.md and the RUN record of the response comparison (caixa 7.9)."""

import json
from typing import Any

from src.config import PROJECT_ROOT
from src.reporting.run_record import RunRecord

DOC = PROJECT_ROOT / "docs" / "RESPONSE_EVALUATION.md"
NOTES = PROJECT_ROOT / "docs" / "response_notes.md"
EVIDENCE = PROJECT_ROOT / "docs" / "evidence" / "response" / "compare.json"
HEAD = (
    "| Estratégia | Valor, revisão perdida (US$ mil) | Δ vs. não fazer nada (US$ mil) | Valor, "
    "revisão decidida depois (US$ mil) | Valor por proposta (US$) | Aprovação | Revisão | "
    "Bad rate dos aprovados |\n|---|---|---|---|---|---|---|---|"
)
POLICY_STRATEGY = "modo conservador por valor (política)"
INTRO = (
    "Cada estratégia decide os lotes a partir do ponto de decisão, o primeiro lote em que a "
    "matriz de resposta pede mais do que registrar. O valor usa o desfecho realizado da "
    "simulação e a economia do [ADR-0016](adr/0016-empirical-cost-threshold.md): bom aprovado "
    "rende o ganho, mau aprovado custa a perda, recusa e revisão valem 0 no lote. Recalibrar e "
    "retreinar usam só o que é observável no ponto de decisão (GR-7, GR-8) e valem a partir "
    "do lote seguinte. Decisões em [ADR-0012](adr/0012-guardrails-conservative-mode.md) e "
    "[ADR-0013](adr/0013-retraining-gate-rollback.md).\n"
)


def _k(v: float | None) -> str:
    return (
        "—"
        if v is None
        else f"{v / 1000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )


def _pct(v: float) -> str:
    return f"{100 * v:.1f}%".replace(".", ",")


def _row(r: dict[str, Any]) -> str:
    return (f"| {r['strategy']} | {_k(r['value'])} | {_k(r['delta_vs_nothing'])} | "
            f"{_k(r['value_review_recovered'])} | {r['value_per_app']:.0f} | "
            f"{_pct(r['approval_rate'])} | {_pct(r['review_rate'])} | "
            f"{_pct(r['bad_rate_approved'])} |")  # fmt: skip


def _gate(g: dict[str, Any]) -> str:
    parts = []
    for k, v in g["checks"].items():
        verdict = "ok" if v["passed"] else "falhou"
        parts.append(f"`{k}` {v['value']:.4f} (limite {v['limit']}) {verdict}")
    checks = "; ".join(parts)
    return (
        f"Gate do challenger (GR-5): **{'aprovado' if g['passed'] else 'reprovado'}** — {checks}."
    )


def scenario_section(s: dict[str, Any]) -> list[str]:
    """Header, gate verdict and table of one scenario."""
    return [f"\n## {s['scenario']}\n",
            f"Ponto de decisão: lote {s['decision_point']} ({s['batches']} lotes avaliados). "
            f"Regra da matriz: **{s['rule']}** — {s['situation']} "
            f"(ações {', '.join(s['actions'])}).\n",
            _gate(s["gate"]) + "\n", HEAD, *[_row(r) for r in s["rows"]]]  # fmt: skip


def render(body: dict[str, Any]) -> str:
    """Whole document."""
    lines = ["# Comparação de respostas à degradação\n",
             "> Gerado por `make respond-compare` (`src/response/docs.py`). Não editar à mão.\n",
             f"RUN: [{body['run_id']}](runs/{body['run_id']}.md).\n", INTRO]  # fmt: skip
    for s in body["scenarios"]:
        lines += scenario_section(s)
    if NOTES.exists():
        lines += ["", NOTES.read_text(encoding="utf-8").rstrip()]
    return "\n".join(lines) + "\n"


def write_doc(body: dict[str, Any]) -> None:
    """Write docs/RESPONSE_EVALUATION.md."""
    DOC.write_text(render(body), encoding="utf-8", newline="\n")


def compare_record(results: list[dict[str, Any]], run_id: str, git: tuple[str, bool]) -> RunRecord:
    """RUN record (kind ``response``): value of each strategy per scenario, in US$ thousand."""
    metrics = {s["scenario"]: {r["strategy"]: round(r["value"] / 1000, 1) for r in s["rows"]}
               for s in results}  # fmt: skip
    policy = {s["scenario"]: next(r for r in s["rows"] if r["strategy"] == POLICY_STRATEGY)
              for s in results}  # fmt: skip
    deltas = "; ".join(f"{k}: {_k(v['delta_vs_nothing'])}" for k, v in policy.items())
    return RunRecord(
        run_id=run_id, kind="response", scenario="ALL", seed=0, data_hash="—",
        model="champion", mlflow_ref="—", metrics=metrics, sha=git[0], dirty=git[1],
        verdict=f"política (modo conservador por valor) vs. não fazer nada, US$ mil — {deltas}",
        artifacts=["docs/evidence/response/compare.json", "docs/RESPONSE_EVALUATION.md"],
        notes=["Valores em US$ mil, somados do ponto de decisão ao último lote."],
    )  # fmt: skip


def drill_record(body: dict[str, Any], run_id: str, git: tuple[str, bool]) -> RunRecord:
    """RUN record of the shadow evaluation and the promotion/rollback drill."""
    passed = [r["batch"] for r in body["shadow"] if r.get("gate_passed")]
    d = body["drill"]
    gate = f"aprovado no lote {passed[0]}" if passed else "nunca aprovado"
    verdict = (f"gate na sombra: {gate}"
               f" · rollback restaurou o anterior: {d['rollback_restored_previous']}"
               f" · rollback reversível: {d['rollback_reversible']}")  # fmt: skip
    metrics = {f"lote {r['batch']}": {k: round(v, 4) for k, v in r["matured"].items()}
               for r in body["shadow"] if "matured" in r}  # fmt: skip
    return RunRecord(
        run_id=run_id,
        kind="response",
        scenario="DRILL",
        seed=0,
        data_hash="—",
        model=f"{d['model']} (ensaio)",
        mlflow_ref="experimento `response`",
        metrics=metrics,
        verdict=verdict,
        sha=git[0],
        dirty=git[1],
        artifacts=["docs/evidence/response/shadow_drill.json"],
        extra={"cenário": body["scenario"], "challenger treinado no lote": body["trained_at"]},
    )


def main() -> None:
    """Regenerate the document from the committed evidence (after editing the notes)."""
    body = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    write_doc(body)


if __name__ == "__main__":
    main()
