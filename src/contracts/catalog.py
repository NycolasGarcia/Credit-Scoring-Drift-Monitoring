"""Render ``docs/DATA_CONTRACTS.md`` from the rule catalog, the contract config and the
defect catalog, so the documented rules can never drift from the enforced ones.
"""

from src.config import PROJECT_ROOT
from src.contracts.rules import RULES
from src.contracts.settings import ContractConfig, load_contract_config
from src.simulation.bad_batch import DEFECTS

DOC = PROJECT_ROOT / "docs" / "DATA_CONTRACTS.md"
HEADER = """# Contratos de dados

> Gerado por `make contracts-doc` (`src/contracts/catalog.py`) a partir de `src/contracts/rules.py`,
> `config/contracts/contract.yaml` e `src/simulation/bad_batch.py`. Não editar à mão.
> Decisões de desenho: [ADR-0008](adr/0008-data-contracts.md).

O contrato de **entrada** valida cada lote de propostas antes da pontuação; o de **saída**
valida o lote pontuado. Biblioteca: Pandera 0.36 (`pandera.pandas`), validação `lazy`
(todas as falhas coletadas), `strict=True` (coluna fora do contrato bloqueia), sem coerção
de tipo.

**Política do gate (GR-1, GR-2):**

- escopo `schema` ou `batch` com falha → **lote bloqueado**: 0 linhas pontuadas, exit code 2,
  alerta `CONTRACT_BATCH_BLOCKED`, lote inteiro em `data/quarantine/<batch_id>/`;
- escopo `row` com falha → **linhas em quarentena**, restante pontuado; se a fração de linhas
  reprovadas passar de {max_rate:.0%} → lote bloqueado (fonte suspeita);
- regras `soft` → só aviso no relatório e no log;
- relatório de violação **só com agregados** (regra, escopo, contagem, taxas, nomes de
  categorias novas) — nenhum valor de linha (GR-10).
"""


def rules_table() -> str:
    """Markdown table of every rule with the defect that trips it in isolation."""
    tests = {}
    for d in DEFECTS.values():
        tests.setdefault(d.expected_rule, []).append(f"`{d.name}`")
    rows = ["| Regra | Severidade | Escopo | O que garante | Defeito que a dispara isoladamente |",
            "|---|---|---|---|---|"]  # fmt: skip
    for r in RULES.values():
        tested = ", ".join(tests.get(r.id, [])) or "teste direto em `tests/test_contracts.py`"
        rows.append(f"| {r.id} | {r.severity} | {r.scope} | {r.description} | {tested} |")
    return "\n".join(rows)


def parameters(cfg: ContractConfig) -> str:
    """Contract parameters as configured."""
    lines = [f"- `{c}`: [{lo:g}, {hi:g}]" for c, (lo, hi) in cfg.input.ranges.items()]
    lines += [f"- domínio `{c}`: {v}" for c, v in cfg.input.domains.items()]
    lines += [f"- sentinela `{c}`: {v}" for c, v in cfg.input.sentinels.items()]
    scale, window = cfg.batch.income_scale, cfg.batch.issue_date_window
    lines += [f"- coerência da parcela: erro relativo ≤ {cfg.input.installment_tolerance:.0%}",
              f"- escala da renda do lote: mediana / referência ∈ "
              f"[{scale.min_ratio:g}, {scale.max_ratio:g}]",
              f"- janela de emissão: {window.min} a {window.max}",
              f"- campos obrigatórios: {', '.join(cfg.input.required)}",
              f"- não negativos: {', '.join(cfg.input.non_negative)}"]  # fmt: skip
    return "\n".join(lines)


def render(cfg: ContractConfig) -> str:
    """Whole document body (the D6 discussion lives in the hand-written appendix file)."""
    appendix = (PROJECT_ROOT / "docs" / "contracts_d6.md").read_text(encoding="utf-8")
    return (
        HEADER.format(max_rate=cfg.batch.max_row_failure_rate)
        + "\n## Regras\n\n" + rules_table()
        + f"\n\n## Parâmetros (contrato v{cfg.version})\n\n" + parameters(cfg)
        + "\n\n" + appendix
    )  # fmt: skip


if __name__ == "__main__":
    DOC.write_text(render(load_contract_config()), encoding="utf-8")
