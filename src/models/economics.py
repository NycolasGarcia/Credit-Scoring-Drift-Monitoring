"""Realized decision economics from the lender's cash flows (ADR-0016).

Reads the inventory columns marked ``use: custo`` (payments, recoveries, fees) to measure,
in aggregate, what approving a loan actually returned. These columns are post-origination:
they are never model features and never leave this module at row level.

Net cash per approved loan = total_pymnt - funded_amnt - collection_recovery_fee
(``total_pymnt`` = principal + interest + late fees + recoveries, verified on the raw data).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
from pyarrow import csv as pacsv

from src.data.inventory import load_inventory
from src.data.pseudonymize import pseudonymize_ids
from src.data.target import map_target

ORIGINATION_INPUTS = ("id", "loan_status", "term", "installment")


def cost_columns() -> list[str]:
    """Columns the inventory allows for economics estimation."""
    return load_inventory().by_use("custo")


def read_cost_frame(path: Path, key: str) -> pd.DataFrame:
    """Read cost columns keyed by ``loan_key``; the raw id is dropped immediately."""
    cols = [*ORIGINATION_INPUTS, *cost_columns()]
    types = {c: pa.float64() for c in cols} | {
        c: pa.string() for c in ("id", "loan_status", "term")
    }
    opts = pacsv.ConvertOptions(include_columns=cols, column_types=types, strings_can_be_null=True)
    df = pacsv.read_csv(path, convert_options=opts).to_pandas()
    df = df[df["loan_status"].notna()].copy()
    df["term"] = pd.to_numeric(df["term"].str.extract(r"(\d+)")[0], errors="coerce")
    df["loan_key"] = pseudonymize_ids(df["id"], key)
    df["target"] = map_target(df["loan_status"])
    return df.drop(columns=["id", "loan_status"])


def realized_economics(df: pd.DataFrame) -> pd.DataFrame:
    """Add contractual interest, realized net cash, loss rate and interest realization."""
    out = df.copy()
    out["contractual_interest"] = (out["installment"] * out["term"] - out["funded_amnt"]).clip(
        lower=0
    )
    out["net_cash"] = out["total_pymnt"] - out["funded_amnt"] - out["collection_recovery_fee"]
    out["loss_rate"] = -out["net_cash"] / out["funded_amnt"]
    contractual = out["contractual_interest"].replace(0, np.nan)
    out["interest_realization"] = out["total_rec_int"] / contractual
    return out


def estimate_premises(econ: pd.DataFrame) -> dict[str, float]:
    """Dollar-weighted LGD (bad loans) and interest realization (good loans), plus spread."""
    bad, good = econ[econ["target"] == 1], econ[econ["target"] == 0]
    lgd = float(-bad["net_cash"].sum() / bad["funded_amnt"].sum())
    margin = float(good["total_rec_int"].sum() / good["contractual_interest"].sum())
    return {
        "lgd": lgd,
        "margin_realization": margin,
        "n_bad": len(bad),
        "n_good": len(good),
        "loss_rate_p25": float(bad["loss_rate"].quantile(0.25)),
        "loss_rate_median": float(bad["loss_rate"].median()),
        "loss_rate_p75": float(bad["loss_rate"].quantile(0.75)),
        "interest_realization_median": float(good["interest_realization"].median()),
    }


def net_of_funding(df: pd.DataFrame, funding_rate: float) -> np.ndarray:
    """Net cash after the cost of funding the outstanding balance.

    Interest accrues as rate x integral(balance dt), so balance-years = total_rec_int / rate;
    funding cost = funding_rate x balance-years. No loan duration assumption is needed.
    """
    balance_years = df["total_rec_int"] / (df["int_rate"] / 100)
    return (df["net_cash"] - funding_rate * balance_years).to_numpy()


def realized_value(net_cash: np.ndarray, p: np.ndarray, threshold: float) -> float:
    """Actual net cash per application of approving every score below ``threshold``."""
    return float(np.sum(net_cash * (p < threshold)) / len(p))


def confusion_costs(
    y: np.ndarray, p: np.ndarray, net_cash: np.ndarray, threshold: float
) -> dict[str, float]:
    """Counts and realized money behind each cell of the decision confusion matrix.

    Positive class = bad. FN = bad approved (realized loss); FP = good rejected (forgone gain).
    """
    approved = p < threshold
    fn, tp = approved & (y == 1), ~approved & (y == 1)
    tn, fp = approved & (y == 0), ~approved & (y == 0)
    return {
        "tn": int(tn.sum()), "fp": int(fp.sum()), "fn": int(fn.sum()), "tp": int(tp.sum()),
        "fn_loss_total": float(-net_cash[fn].sum()),
        "fp_forgone_total": float(net_cash[fp].sum()),
        "fn_loss_mean": float(-net_cash[fn].mean()) if fn.any() else 0.0,
        "fp_forgone_mean": float(net_cash[fp].mean()) if fp.any() else 0.0,
        "tp_loss_avoided_total": float(-net_cash[tp].sum()),
    }  # fmt: skip
