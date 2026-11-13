"""Bad-batch generator: a catalog of defects, each expected to be caught by a known rule.

Every defect is a pure function (batch, rng, rate) -> corrupted copy. The catalog doubles as
the test oracle: injecting one defect alone must trigger exactly its ``expected_rule``.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

Mutator = Callable[[pd.DataFrame, np.random.Generator, float], pd.DataFrame]


@dataclass(frozen=True)
class Defect:
    """One corruption and the contract rule that must catch it."""

    name: str
    expected_rule: str
    description: str
    apply: Mutator


def _rows(df: pd.DataFrame, rng: np.random.Generator, rate: float) -> np.ndarray:
    n = max(1, round(len(df) * rate))
    return rng.choice(df.index.to_numpy(), size=n, replace=False)


def _set(col: str, value) -> Mutator:
    def mutate(df, rng, rate):
        out = df.copy()
        out.loc[_rows(out, rng, rate), col] = value
        return out

    return mutate


def _scale(col: str, factor: float, whole_batch: bool = False) -> Mutator:
    def mutate(df, rng, rate):
        out = df.copy()
        idx = out.index if whole_batch else _rows(out, rng, rate)
        out.loc[idx, col] = out.loc[idx, col] * factor
        return out

    return mutate


def _duplicate_keys(df, rng, rate):
    out = df.copy()
    rows = _rows(out, rng, rate)
    out.loc[rows, "loan_key"] = out["loan_key"].iloc[0]
    return out


def _future_date(df, rng, rate):
    out = df.copy()
    out.loc[_rows(out, rng, rate), "issue_d"] = pd.Timestamp("2030-01-01")
    return out


def _extra_column(df, rng, rate):
    return df.assign(recoveries=0.0)


def _missing_column(df, rng, rate):
    return df.drop(columns="dti")


def _int_rate_as_text(df, rng, rate):
    return df.assign(int_rate=df["int_rate"].astype(str))


DEFECTS: dict[str, Defect] = {d.name: d for d in [
    Defect("extra_column", "H01", "coluna pós-originação (recoveries) no lote", _extra_column),
    Defect("missing_column", "H01", "coluna dti ausente", _missing_column),
    Defect("wrong_type", "H02", "int_rate enviado como texto", _int_rate_as_text),
    Defect("duplicate_keys", "H03", "loan_key repetido", _duplicate_keys),
    Defect("null_critical", "H04", "annual_inc nulo", _set("annual_inc", np.nan)),
    Defect("negative_income", "H05", "annual_inc negativo", _scale("annual_inc", -1.0)),
    Defect("unknown_grade", "H06", "grade fora de A-G", _set("grade", "Z")),
    Defect("future_date", "H07", "issue_d no futuro", _future_date),
    Defect("incoherent_installment", "H08", "parcela 50% acima da amortização",
           _scale("installment", 1.5)),
    Defect("sentinel", "H09", "tot_hi_cred_lim = 9.999.999", _set("tot_hi_cred_lim", 9_999_999.0)),
    Defect("monthly_income", "H10", "renda mensal no lugar de anual (D6)",
           _scale("annual_inc", 1 / 12, whole_batch=True)),
    Defect("negative_count", "H11", "open_acc negativo", _set("open_acc", -3.0)),
    Defect("new_category", "S02", "home_ownership com nível inexistente na referência",
           _set("home_ownership", "ANY")),
]}  # fmt: skip


def make_bad_batch(
    base: pd.DataFrame, defects: list[str], seed: int, rate: float
) -> tuple[pd.DataFrame, dict]:
    """Apply defects in order; return the batch and a manifest of what was injected."""
    rng = np.random.default_rng(seed)
    out = base.reset_index(drop=True)
    for name in defects:
        out = DEFECTS[name].apply(out, rng, rate)
    injected = [{"name": n, "expected_rule": DEFECTS[n].expected_rule} for n in defects]
    manifest = {"seed": seed, "rate": rate, "rows": len(out), "defects": injected}
    return out, manifest
