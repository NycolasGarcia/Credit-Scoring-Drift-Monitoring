"""Monitoring job: step events, blocked and failing batches, metrics and private run logs."""

import argparse
import json
import logging
from pathlib import Path
from types import SimpleNamespace

import mlflow
import numpy as np
import pandas as pd
import pytest
from prometheus_client import generate_latest

from src.alerting.settings import load_alert_config
from src.contracts.settings import load_contract_config
from src.data.features import model_feature_columns
from src.logging_config import REDACTED
from src.monitoring.profile import build_profile
from src.monitoring.settings import load_monitoring_config
from src.observability.events import attach_run_log, detach_run_log
from src.observability.metrics import BY_NAME, build_registry
from src.observability.runner import mlflow_key, record, soft_rule_batches
from src.observability.samples import batch_samples
from src.pipeline import BatchInput, JobContext, RunMemory, run_batch
from src.response.guardrails import REASONS
from src.simulation.bad_batch import make_bad_batch
from tests.synthetic import synthetic_batch

FIELDS = {"run_id", "batch_id", "step", "status", "duration_ms", "rows_in", "rows_out",
          "rows_quarantined"}  # fmt: skip


class FixedModel:
    """Scores everyone at 0.1 (approve)."""

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        return np.column_stack([np.full(len(x), 0.9), np.full(len(x), 0.1)])


class BrokenModel:
    """Fails when asked to score."""

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        raise RuntimeError("model store unavailable")


@pytest.fixture(scope="module")
def reference() -> pd.DataFrame:
    return synthetic_batch(6000, seed=31)


@pytest.fixture(scope="module")
def profile(reference: pd.DataFrame) -> dict:
    summary = {"threshold": 0.5, "approval_rate": 0.9, "importance_rank": model_feature_columns(),
               "reference_metrics": {"auc": 0.7}}  # fmt: skip
    return build_profile(reference, pd.Series(np.random.default_rng(1).random(6000)), summary)


def context(reference, profile, model, tmp_path: Path) -> JobContext:
    return JobContext("RUN-TEST", model, "v-test", profile, reference, load_contract_config(),
                      load_monitoring_config(), load_alert_config(), tmp_path / "q")  # fmt: skip


def batch_folder(tmp_path: Path, apps: pd.DataFrame) -> BatchInput:
    folder = tmp_path / "S9-b00"
    folder.mkdir(parents=True, exist_ok=True)
    apps.to_parquet(folder / "applications.parquet", index=False)
    rng = np.random.default_rng(2)
    labels = pd.DataFrame({"loan_key": apps["loan_key"], "target": (rng.random(len(apps)) < 0.1)
                           .astype(float), "p_oracle": 0.1, "label_batch": 0})  # fmt: skip
    labels.to_parquet(folder / "labels.parquet", index=False)
    return BatchInput(0, "S9-b00", "2014-01", folder)


def test_valid_batch_emits_every_step_with_required_fields(reference, profile, tmp_path) -> None:
    item = batch_folder(tmp_path, synthetic_batch(2000, seed=40))
    state = run_batch(context(reference, profile, FixedModel(), tmp_path), item, RunMemory())
    steps = [e["step"] for e in state.log.events]
    assert steps == ["ingest", "validate", "score", "detect", "evaluate", "alert", "respond"]
    assert all(set(e) == FIELDS for e in state.log.events)
    assert {e["step"]: e["status"] for e in state.log.events}["respond"] == "ok"
    assert set(state.decisions["reason_code"]) <= set(REASONS)  # constant scores: AUC 0.5
    assert len(state.scored) == 2000 and state.l4 is not None
    assert state.levels["CDM_SOFT_RULES"] == 1  # 2,000 rows is below the volume band (S03)


def test_blocked_batch_skips_scoring_and_raises_contract_alert(
    reference, profile, tmp_path
) -> None:
    bad, _ = make_bad_batch(synthetic_batch(2000, seed=41), ["monthly_income"], 3, 0.01)
    item = batch_folder(tmp_path, bad)
    state = run_batch(context(reference, profile, FixedModel(), tmp_path), item, RunMemory())
    status = {e["step"]: e["status"] for e in state.log.events}
    assert [status[s] for s in ("score", "detect", "evaluate")] == ["skipped"] * 3
    assert state.diagnosis == "D0" and state.levels["CDM_CONTRACT_BLOCKED"] == 2
    assert state.scored.empty


def test_failing_step_is_recorded_and_alerted(reference, profile, tmp_path) -> None:
    item = batch_folder(tmp_path, synthetic_batch(2000, seed=42))
    state = run_batch(context(reference, profile, BrokenModel(), tmp_path), item, RunMemory())
    status = {e["step"]: e["status"] for e in state.log.events}
    assert status["score"] == "failed" and status["detect"] == "skipped"
    assert state.levels["CDM_STEP_FAILED"] == 2


def test_batch_samples_use_catalog_and_mark_success(reference, profile, tmp_path) -> None:
    item = batch_folder(tmp_path, synthetic_batch(2000, seed=43))
    ok = run_batch(context(reference, profile, FixedModel(), tmp_path), item, RunMemory())
    ok.finished_at = 123.0
    samples = batch_samples(ok, 0.1)
    assert {s[0] for s in samples} <= set(BY_NAME)
    text = generate_latest(build_registry(samples)).decode()
    assert "cdm_feature_psi" in text and "cdm_last_success_timestamp_seconds 123.0" in text
    failed = run_batch(context(reference, profile, BrokenModel(), tmp_path), item, RunMemory())
    assert "cdm_last_success_timestamp_seconds" not in {s[0] for s in batch_samples(failed, 0.1)}


def test_run_log_file_is_json_lines_without_pii(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    handler = attach_run_log(path)
    logging.getLogger("cdm.test").warning("evento", extra={"emp_title": "Gerente", "batch_id": "b"})
    detach_run_log(handler)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records[-1]["emp_title"] == REDACTED and records[-1]["batch_id"] == "b"


def test_mlflow_key_flattens_labels() -> None:
    assert mlflow_key("cdm_feature_psi{feature=dti}") == "cdm_feature_psi/dti"
    assert mlflow_key("cdm_batch_index") == "cdm_batch_index"


@pytest.fixture
def isolated_mlflow(tmp_path: Path):
    """Throwaway tracking store; restores the previous one afterwards."""
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}")
    yield
    mlflow.set_tracking_uri(previous)


def test_child_runs_stay_in_monitoring_experiment(
    reference, profile, tmp_path, isolated_mlflow
) -> None:
    monitoring = mlflow.create_experiment("monitoring", artifact_location=tmp_path.as_uri())
    mlflow.create_experiment("training", artifact_location=tmp_path.as_uri())
    item = batch_folder(tmp_path, synthetic_batch(2000, seed=44))
    state = run_batch(context(reference, profile, FixedModel(), tmp_path), item, RunMemory())
    args = argparse.Namespace(push=False, no_mlflow=False, scenario="S9")
    with mlflow.start_run(run_name="parent", experiment_id=monitoring):
        mlflow.set_experiment("training")  # what loading the champion does mid-run
        record(context(reference, profile, FixedModel(), tmp_path), state, args, monitoring)
    children = mlflow.search_runs(experiment_ids=[monitoring], output_format="list",
                                  filter_string="tags.batch_id = 'S9-b00'")  # fmt: skip
    assert len(children) == 1 and children[0].data.metrics["cdm_batch_index"] == 0


def test_summary_counts_batches_per_soft_rule() -> None:
    states = [SimpleNamespace(report={"soft_warnings": {"S02": {}}}),
              SimpleNamespace(report={"soft_warnings": {"S02": {}, "S01": {}}}),
              SimpleNamespace(report={})]  # fmt: skip
    assert soft_rule_batches(states) == {"soft_S01": 1, "soft_S02": 2}
