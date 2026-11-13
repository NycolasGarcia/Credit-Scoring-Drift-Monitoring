"""Rule catalog: every contract rule has an id, a severity, a scope and a rationale.

Scopes:
    schema -> structural problem; the whole batch is blocked.
    batch  -> statistic of the whole batch is implausible; the whole batch is blocked.
    row    -> the offending rows are quarantined; the batch is blocked only if too many fail.
"""

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass(frozen=True)
class Rule:
    """One contract rule."""

    id: str
    severity: Literal["hard", "soft"]
    scope: Literal["schema", "batch", "row"]
    description: str


RULES: dict[str, Rule] = {r.id: r for r in [
    Rule("H01", "hard", "schema", "colunas exatamente as do contrato (sem extra, sem faltante)"),
    Rule("H02", "hard", "schema", "tipo de cada coluna conforme o contrato"),
    Rule("H03", "hard", "schema", "loan_key único no lote"),
    Rule("H04", "hard", "row", "campos críticos não nulos"),
    Rule("H05", "hard", "row", "valores dentro de faixas possíveis"),
    Rule("H06", "hard", "row", "valores categóricos e prazo dentro do domínio"),
    Rule("H07", "hard", "row", "data de emissão dentro da janela válida (sem data futura)"),
    Rule("H08", "hard", "row", "parcela coerente com valor, taxa e prazo"),
    Rule("H09", "hard", "row", "sem valores sentinela (placeholder de bureau)"),
    Rule("H10", "hard", "batch", "escala da renda do lote compatível com a referência"),
    Rule("H11", "hard", "row", "contagens e saldos não negativos"),
    Rule("S01", "soft", "batch", "taxa de nulos por coluna não sobe além da tolerância"),
    Rule("S02", "soft", "batch", "sem categorias inexistentes na referência"),
    Rule("S03", "soft", "batch", "volume do lote dentro da banda"),
    Rule("S04", "soft", "batch", "cauda extrema de utilização dentro do esperado"),
    Rule("O01", "hard", "schema", "lote pontuado: colunas, tipos e loan_key único"),
    Rule("O02", "hard", "row", "score em [0, 1] e decisão no domínio, sem nulos"),
    Rule("O03", "hard", "batch", "decisão consistente com score e limiar"),
]}  # fmt: skip

BUILTIN_CHECK_TO_RULE = {
    "column_in_schema": "H01",
    "column_in_dataframe": "H01",
    "multiple_fields_uniqueness": "H03",
    "field_uniqueness": "H03",
    "not_nullable": "H04",
}


def rule_of(check: str) -> str:
    """Map a pandera failure-case ``check`` label to a rule id."""
    if check[:3] in RULES:
        return check[:3]
    if check.startswith("dtype("):
        return "H02"
    return BUILTIN_CHECK_TO_RULE.get(check, "H02")


def classify(failure_cases: pd.DataFrame) -> pd.DataFrame:
    """Add ``rule`` and ``scope`` columns to pandera failure cases (values are dropped)."""
    out = failure_cases[["column", "check", "index"]].copy()
    out["rule"] = out["check"].astype(str).map(rule_of)
    out["scope"] = out["rule"].map(lambda r: RULES[r].scope)
    return out
