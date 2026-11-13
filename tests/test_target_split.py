"""Target mapping, maturity, pseudonymization and reference x production separation."""

import numpy as np
import pandas as pd
import pytest

from src.data.pseudonymize import pseudonymize_ids
from src.data.split import SplitConfig, assign_partitions, content_hash
from src.data.target import is_mature, map_target, maturity_date
from tests.conftest import TEST_KEY

CFG = SplitConfig(
    scope_application_type="Individual", reference_start="2013-01", reference_end="2013-12",
    production_start="2014-01", holdout_fraction=0.2, seed=42,
)  # fmt: skip


def test_target_mapping() -> None:
    status = pd.Series(["Fully Paid", "Charged Off", "Default", "Current", "Late (31-120 days)"])
    out = map_target(status)
    assert out.tolist()[:3] == [0.0, 1.0, 1.0]
    assert out.iloc[3:].isna().all()


def test_unknown_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown loan_status"):
        map_target(pd.Series(["Fully Paid", "Restructured"]))


def test_maturity_date_and_flag() -> None:
    issue = pd.Series(pd.to_datetime(["2013-05-01", "2016-04-01"]))
    term = pd.Series([36.0, 36.0])
    assert maturity_date(issue, term).dt.strftime("%Y-%m").tolist() == ["2016-05", "2019-04"]
    assert is_mature(issue, term, pd.Timestamp("2019-03-01")).tolist() == [True, False]


def test_pseudonymization_is_keyed_and_deterministic() -> None:
    ids = pd.Series(["123", "456", "123"])
    a, b = pseudonymize_ids(ids, TEST_KEY), pseudonymize_ids(ids, TEST_KEY + "x")
    assert a.iloc[0] == a.iloc[2] and a.iloc[0] != a.iloc[1]
    assert not (a == b).any()
    assert not a.str.contains("123").any()


def test_pseudonymization_requires_key() -> None:
    with pytest.raises(ValueError, match="key"):
        pseudonymize_ids(pd.Series(["1"]), "")


def test_reference_and_production_do_not_overlap(loans: pd.DataFrame) -> None:
    part = assign_partitions(loans, CFG)
    ids = {p: set(loans.loc[part == p, "id"]) for p in ("reference", "holdout", "production")}
    assert not ids["reference"] & ids["production"]
    assert not ids["holdout"] & ids["production"]
    assert not ids["reference"] & ids["holdout"]


def test_partitions_respect_time_and_scope(loans: pd.DataFrame) -> None:
    part = assign_partitions(loans, CFG)
    ref = loans[part.isin(["reference", "holdout"])]
    prod = loans[part == "production"]
    assert ref["issue_d"].dt.year.eq(2013).all() and ref["is_mature"].all()
    assert ref["target"].notna().all()
    assert (prod["issue_d"] >= "2014-01-01").all()
    assert loans.loc[part != "out_of_scope", "application_type"].eq("Individual").all()


def test_holdout_fraction_and_determinism(loans: pd.DataFrame) -> None:
    a, b = assign_partitions(loans, CFG), assign_partitions(loans, CFG)
    assert a.equals(b)
    share = (a == "holdout").sum() / a.isin(["reference", "holdout"]).sum()
    assert np.isclose(share, CFG.holdout_fraction, atol=0.02)


def test_content_hash_detects_change(loans: pd.DataFrame) -> None:
    changed = loans.copy()
    changed.loc[0, "term"] = 99.0
    assert content_hash(loans) == content_hash(loans.copy())
    assert content_hash(loans) != content_hash(changed)
