"""``docs/FAIRNESS.md`` and the RUN record of the bias analysis (generated, not edited)."""

import json
from typing import Any

import numpy as np

from src.config import PROJECT_ROOT
from src.reporting.run_record import RunRecord

DOC = PROJECT_ROOT / "docs" / "FAIRNESS.md"
NOTES = PROJECT_ROOT / "docs" / "fairness_notes.md"
EVIDENCE = PROJECT_ROOT / "docs" / "evidence" / "governance" / "fairness.json"


def _p(v: float | None, digits: int = 1) -> str:
    return "—" if v is None else f"{100 * v:.{digits}f}%".replace(".", ",")


def _n(v: float | None, digits: int = 3) -> str:
    return "—" if v is None else f"{v:.{digits}f}".replace(".", ",")


def group_rows(table: dict[str, dict[str, Any]]) -> list[str]:
    """Group table of one segment."""
    rows = ["| Grupo | Propostas | Aprovação | Aprovação dos bons | Aprovação dos maus | Bad rate "
            "| Calibração (obs/esp) | AUC |", "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for g, m in table.items():
        rows.append(f"| {g} | {m['n']:,} | {_p(m['approval_rate'])} | "
                    f"{_p(m['good_approval_rate'])} | {_p(m['bad_approval_rate'])} | "
                    f"{_p(m['bad_rate'])} | {_n(m['calibration_ratio'], 2)} | "
                    f"{_n(m['auc'])} |".replace(",", "."))  # fmt: skip
    return rows


def reference_part(ref: dict[str, Any], min_size: int) -> list[str]:
    """Normal regime: champion on the 2013 test split."""
    out = [f"## Regime normal (teste de 2013, {ref['rows']:,} propostas)\n".replace(",", "."),
           f"O champion aprova {_p(ref['approval_rate'])} das propostas no limiar da política. "
           f"Gaps entre grupos com pelo menos {min_size} propostas.\n"]  # fmt: skip
    for col, s in ref["segments"].items():
        g = s["gaps"]
        out += [f"\n### `{col}`\n", f"Gap de aprovação {_p(g['approval_rate'], 2)} · gap de "
                f"aprovação dos bons {_p(g['good_approval_rate'], 2)} · gap de calibração "
                f"{_n(g['calibration_ratio'], 2)}.\n"]  # fmt: skip
        if col != "addr_state":
            out += group_rows(s["groups"])
    return out


def proxy_part(proxy: dict[str, float]) -> list[str]:
    """Association of the model features with the region."""
    rows = ["\n## Força de proxy da região\n",
            "Cramér's V entre `addr_state` (fora do modelo) e cada feature do modelo (numéricas "
            "em decis); 0 = nenhuma associação, 1 = a feature determina a região.\n",
            "| Feature | Cramér's V |", "|---|---|"]  # fmt: skip
    return rows + [f"| `{f}` | {_n(v)} |" for f, v in proxy.items()]


def _gap_stats(per_batch: list[dict[str, Any]], col: str) -> str:
    vals = [b[col] for b in per_batch if b[col] is not None]
    return "—" if not vals else f"{_p(float(np.mean(vals)))} (máx. {_p(max(vals))})"


def scenario_part(s: dict[str, Any]) -> list[str]:
    """The three decisions of one scenario: value and approval gaps per segment."""
    out = [f"\n### {s['scenario']} (do lote {s['decision_point']} em diante)\n",
           "| Decisão | Valor vs. champion puro (US$ mil) | Gap `home_ownership` | "
           "Gap `emp_length` | Gap `addr_state` |", "|---|---|---|---|---|"]  # fmt: skip
    for name, r in s["strategies"].items():
        delta = f"{r['delta_vs_champion'] / 1000:,.0f}".replace(",", ".")
        out.append(f"| {name} | {delta} | {_gap_stats(r['per_batch'], 'home_ownership')} | "
                   f"{_gap_stats(r['per_batch'], 'emp_length')} | "
                   f"{_gap_stats(r['per_batch'], 'addr_state')} |")  # fmt: skip
    for name in list(s["strategies"])[1:]:
        out += [
            f"\nPor grupo de `home_ownership`, {name}:\n",
            *group_rows(s["strategies"][name]["home_ownership"]),
        ]
    return out


def render(body: dict[str, Any]) -> str:
    """Whole document."""
    cfg = body["config"]
    lines = [
        "# Análise de vieses\n",
        "> Gerado por `make fairness` (`src/governance/report_doc.py`). Não editar à mão.\n",
        f"RUN: [{body['run_id']}](runs/{body['run_id']}.md). Grupos disponíveis no dado: "
        "`home_ownership`, faixas de `emp_length` e `addr_state` (não há gênero nem idade). "
        '"Aprovação dos bons" é a aprovação entre quem pagou (igualdade de oportunidade).\n',
        *reference_part(body["reference"], cfg["min_group_size"]),
        *proxy_part(body["proxy_addr_state"]),
        "\n## Modo conservador (fairness drift)\n",
        "Gap médio por lote entre grupos com pelo menos "
        f"{cfg['min_batch_group_rows']} propostas no lote, e o máximo entre os lotes.\n",
    ]
    for s in body["scenarios"]:
        lines += scenario_part(s)
    if NOTES.exists():
        lines += ["", NOTES.read_text(encoding="utf-8").rstrip()]
    return "\n".join(lines) + "\n"


def write_doc(body: dict[str, Any]) -> None:
    """Write docs/FAIRNESS.md."""
    DOC.write_text(render(body), encoding="utf-8", newline="\n")


def fairness_record(body: dict[str, Any], run_id: str, git: tuple[str, bool]) -> RunRecord:
    """RUN record (kind ``fairness``)."""
    metrics, parts = {}, []
    for s in body["scenarios"]:
        for name, r in s["strategies"].items():
            ho = [b["home_ownership"] for b in r["per_batch"] if b["home_ownership"] is not None]
            metrics[f"{s['scenario']} · {name}"] = {
                "valor vs. champion (US$ mil)": round(r["delta_vs_champion"] / 1000, 1),
                "gap home_ownership máx. (p.p.)": round(100 * max(ho), 1) if ho else None,
            }
        pol = s["strategies"]["conservador com limite (política)"]["delta_vs_champion"]
        raw = s["strategies"]["conservador sem limite"]["delta_vs_champion"]
        parts.append(f"{s['scenario']}: custo do limite US$ {(raw - pol) / 1000:,.0f} mil")
    return RunRecord(
        run_id=run_id, kind="fairness", scenario="ALL", seed=0, data_hash="—", model="champion",
        mlflow_ref="—", metrics=metrics, sha=git[0], dirty=git[1], verdict="; ".join(parts),
        artifacts=["docs/evidence/governance/fairness.json", "docs/FAIRNESS.md"],
    )  # fmt: skip


def main() -> None:
    """Regenerate the document from the committed evidence (after editing the notes)."""
    write_doc(json.loads(EVIDENCE.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
