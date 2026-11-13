"""Loader on a tiny synthetic CSV with the real header (no real data)."""

from pathlib import Path

import pandas as pd

from src.data.inventory import load_inventory
from src.data.load import load_dataset


def _write_csv(path: Path) -> None:
    cols = list(load_inventory().columns)
    rows = pd.DataFrame([dict.fromkeys(cols, "") for _ in range(3)])
    rows.loc[0, ["id", "loan_status", "issue_d", "term", "emp_length", "last_pymnt_d"]] = [
        "1", "Fully Paid", "Jan-2013", " 36 months", "10+ years", "Feb-2016"]  # fmt: skip
    rows.loc[1, ["id", "loan_status", "issue_d", "term", "emp_length", "last_pymnt_d"]] = [
        "2", "Charged Off", "Mar-2013", " 60 months", "< 1 year", "Mar-2019"]  # fmt: skip
    rows.loc[0:1, ["loan_amnt", "recoveries", "emp_title"]] = ["1000", "50", "Some Title"]
    rows.loc[2, "id"] = "Total amount funded in policy code 1: 123"
    rows.to_csv(path, index=False)


def test_loader_drops_footer_parses_and_skips_forbidden(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    _write_csv(path)
    df, snapshot = load_dataset(path)
    assert len(df) == 2
    assert snapshot == pd.Timestamp("2019-03-01")
    assert df["term"].tolist() == [36.0, 60.0]
    assert df["emp_length"].tolist() == [10.0, 0.0]
    assert {"recoveries", "emp_title", "last_pymnt_d"}.isdisjoint(df.columns)
