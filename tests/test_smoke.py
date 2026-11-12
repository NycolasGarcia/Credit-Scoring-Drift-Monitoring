"""Smoke tests: the package imports and core infrastructure works."""

import json
import logging

import pandas as pd

import src
from src.config import Settings, get_settings
from src.logging_config import REDACTED, JsonFormatter, PrivacyFilter


def test_package_imports() -> None:
    assert src.__doc__


def test_settings_load() -> None:
    assert isinstance(get_settings(), Settings)


def test_secret_never_rendered() -> None:
    settings = Settings(pseudonymization_key="super-secret-value")
    assert "super-secret-value" not in repr(settings)
    assert "super-secret-value" not in settings.model_dump_json()


def _render(**extra: object) -> dict:
    record = logging.makeLogRecord({"msg": "event", "levelname": "INFO", **extra})
    PrivacyFilter().filter(record)
    return json.loads(JsonFormatter().format(record))


def test_json_log_keeps_aggregates() -> None:
    out = _render(run_id="RUN-1", rows_in=1000, psi=0.12)
    assert out["run_id"] == "RUN-1"
    assert out["rows_in"] == 1000


def test_privacy_filter_redacts_pii_fields() -> None:
    out = _render(emp_title="Engineer", zip_code="123xx")
    assert out["emp_title"] == REDACTED
    assert out["zip_code"] == REDACTED


def test_privacy_filter_redacts_row_level_values() -> None:
    out = _render(batch=pd.DataFrame({"a": [1, 2]}), values=list(range(100)))
    assert out["batch"] == REDACTED
    assert out["values"] == REDACTED
