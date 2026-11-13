"""Realized economics: net cash, dollar-weighted premises and FP/FN money (synthetic)."""

import numpy as np
import pandas as pd
import pytest

from src.data.features import model_feature_columns
from src.data.inventory import load_inventory
from src.data.load import columns_to_load
from src.models.economics import (
    confusion_costs,
    cost_columns,
    estimate_premises,
    net_of_funding,
    realized_economics,
    realized_value,
)


def _loans() -> pd.DataFrame:
    # loan A: good, pays all interest; loan B: bad, recovers part of the principal
    return pd.DataFrame({
        "target": [0.0, 1.0],
        "installment": [110.0, 110.0], "term": [10.0, 10.0], "funded_amnt": [1000.0, 1000.0],
        "total_pymnt": [1100.0, 400.0], "total_rec_int": [100.0, 50.0],
        "collection_recovery_fee": [0.0, 20.0],
    })  # fmt: skip


def test_realized_economics_net_cash_and_rates() -> None:
    econ = realized_economics(_loans())
    assert econ["net_cash"].tolist() == [100.0, -620.0]
    assert econ["loss_rate"].tolist() == [-0.1, 0.62]
    assert econ["interest_realization"].iloc[0] == 1.0


def test_premises_are_dollar_weighted() -> None:
    prem = estimate_premises(realized_economics(_loans()))
    assert prem["lgd"] == pytest.approx(0.62)
    assert prem["margin_realization"] == pytest.approx(1.0)
    assert (prem["n_bad"], prem["n_good"]) == (1, 1)


def test_realized_value_and_confusion_costs() -> None:
    y, p, net = (
        np.array([0, 1, 0, 1]),
        np.array([0.1, 0.2, 0.8, 0.9]),
        np.array([100.0, -600.0, 80.0, -500.0]),
    )
    assert realized_value(net, p, 0.5) == pytest.approx((100 - 600) / 4)
    cc = confusion_costs(y, p, net, 0.5)
    assert (cc["tn"], cc["fn"], cc["fp"], cc["tp"]) == (1, 1, 1, 1)
    assert cc["fn_loss_total"] == 600.0 and cc["fp_forgone_total"] == 80.0
    assert cc["tp_loss_avoided_total"] == 500.0


def test_funding_cost_uses_balance_years_from_interest() -> None:
    econ = realized_economics(_loans())
    econ["int_rate"] = [10.0, 10.0]
    # balance-years = interest / rate: 100 / 0.10 = 1000 and 50 / 0.10 = 500
    out = net_of_funding(econ, 0.05)
    assert out.tolist() == pytest.approx([100.0 - 50.0, -620.0 - 25.0])
    assert net_of_funding(econ, 0.0).tolist() == econ["net_cash"].tolist()


def test_cost_columns_never_reach_model_or_loader() -> None:
    cost = set(cost_columns())
    assert cost == set(load_inventory().by_use("custo")) and cost
    assert not cost & set(model_feature_columns())
    assert not cost & set(columns_to_load())
