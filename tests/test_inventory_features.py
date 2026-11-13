"""Leakage guard: the model allowlist never contains post-origination or identifying columns."""

import pandas as pd
import pytest

from src.config import get_settings
from src.data.features import model_feature_columns, raw_feature_columns
from src.data.inventory import PII_EXPORT_PATH, load_inventory
from src.data.load import columns_to_load

EXPECTED_RAW_COLUMNS = 151


def test_inventory_covers_every_raw_column() -> None:
    assert len(load_inventory().columns) == EXPECTED_RAW_COLUMNS


def test_inventory_matches_real_header_when_available() -> None:
    path = get_settings().raw_data_path
    if not path.exists():
        pytest.skip("raw dataset not available (CI)")
    header = pd.read_csv(path, nrows=0).columns
    assert set(header) == set(load_inventory().columns)


def test_allowlist_has_no_post_origination_column() -> None:
    post = set(load_inventory().by_category("pos_originacao"))
    assert post, "inventory must list post-origination columns"
    assert not post & set(model_feature_columns())


def test_allowlist_is_origination_only() -> None:
    inv = load_inventory()
    assert all(inv.columns[c].cat == "originacao" for c in raw_feature_columns())


def test_no_direct_identifier_or_free_text_in_model() -> None:
    inv = load_inventory()
    banned = {c for c, s in inv.columns.items() if s.pii == "direto" or s.cat == "texto_livre"}
    assert not banned & set(model_feature_columns())


def test_loader_never_reads_free_text_or_leaky_columns() -> None:
    inv = load_inventory()
    loaded = set(columns_to_load())
    assert not loaded & set(inv.by_category("texto_livre"))
    assert loaded & set(inv.by_category("pos_originacao")) == {"last_pymnt_d"}


def test_exported_pii_list_is_in_sync() -> None:
    exported = PII_EXPORT_PATH.read_text(encoding="utf-8").split()
    assert exported == load_inventory().publish_forbidden()
