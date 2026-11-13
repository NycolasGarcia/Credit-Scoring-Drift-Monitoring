"""Training job (``make train``): candidates -> calibration -> selection -> champion.

Each candidate is one MLflow run in experiment ``training`` and one RUN record. The
champion gets a cost-based threshold, permutation importance, the reference profile
and the ``champion`` alias in the Model Registry.
"""

import json
import logging

import mlflow
import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import PROJECT_ROOT, get_settings
from src.logging_config import configure_logging
from src.models import champion as champ_mod
from src.models.calibration import choose_calibration
from src.models.dataset import internal_split, load_partition, oot_sets, xy
from src.models.evaluate import (
    CandidateResult,
    cv_auc,
    evaluate_sets,
    score_stability,
    select_champion,
)
from src.models.factory import build_model
from src.models.registry import register_champion, setup_tracking
from src.models.settings import TrainingConfig, load_cost_config, load_training_config
from src.monitoring.profile import build_profile, write_profile
from src.reporting.run_record import RunRecord, next_run_id, write_record

logger = logging.getLogger(__name__)
PROFILE_PATH = PROJECT_ROOT / "models" / "reference_profile.json"


def reference_hash() -> str:
    """Content hash of the reference partition, from the split manifest."""
    manifest = get_settings().data_dir / "processed" / "split_manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["partitions"]["reference"][
        "content_sha256"
    ]


def prepare_sets(cfg: TrainingConfig) -> dict[str, pd.DataFrame]:
    """train / calib_fit / calib_select / calibration / test plus OOT windows."""
    sets = internal_split(load_partition("reference"), cfg)
    cal = sets["calibration"]
    fit, sel = train_test_split(cal, test_size=0.5, random_state=cfg.seed, stratify=cal["target"])
    return {**sets, "calib_fit": fit, "calib_select": sel,
            **oot_sets(load_partition("production"), cfg)}  # fmt: skip


def fit_candidate(name: str, sets: dict, cfg: TrainingConfig) -> CandidateResult:
    """Fit, calibrate and evaluate one candidate inside its own MLflow run."""
    params = cfg.models[name]
    x_tr, y_tr = xy(sets["train"])
    with mlflow.start_run(run_name=name) as run:
        cv = cv_auc(build_model(name, params, cfg.seed, cfg.log_features), x_tr, y_tr, cfg)
        raw = build_model(name, params, cfg.seed, cfg.log_features).fit(x_tr, y_tr)
        method, model, briers = "none", raw, {}
        if name != "dummy":
            (xf, yf), (xs, ys) = xy(sets["calib_fit"]), xy(sets["calib_select"])
            method, model, briers = choose_calibration(raw, xf, yf, xs, ys, cfg.calibration_methods)
        result = CandidateResult(name, run.info.run_id, model, method, briers)
        result.metrics = {"cv_train": cv, "test_raw": evaluate_sets(raw, {"t": sets["test"]})["t"],
                          **evaluate_sets(model, _eval_sets(sets, cfg))}  # fmt: skip
        result.score_psi = score_stability(model, sets["test"], _oot(sets, cfg))
        result.model_uri = _log_run(result, params, cfg.skops_trusted_types)
    return result


def _oot(sets: dict, cfg: TrainingConfig) -> dict[str, pd.DataFrame]:
    return {k: sets[k] for k in cfg.oot_windows}


def _eval_sets(sets: dict, cfg: TrainingConfig) -> dict[str, pd.DataFrame]:
    return {"test": sets["test"], **_oot(sets, cfg)}


def _log_run(result: CandidateResult, params: dict, trusted: list[str]) -> str:
    """Log params, metrics and the calibrated model; return the logged model URI."""
    mlflow.log_params({**params, "model": result.name, "calibration": result.calibration})
    for set_name, values in result.metrics.items():
        mlflow.log_metrics({f"{set_name}_{k}": v for k, v in values.items()})
    mlflow.log_metrics({f"score_psi_{k}": v for k, v in result.score_psi.items()})
    mlflow.log_metrics({f"brier_calib_{k}": v for k, v in result.briers.items()})
    info = mlflow.sklearn.log_model(result.model, name="model", skops_trusted_types=trusted)
    return info.model_uri


def finalize(champ: CandidateResult, sets: dict, cfg: TrainingConfig) -> dict:
    """Threshold, importance, profile and registration for the selected model."""
    cost = load_cost_config()
    thresholds = champ_mod.choose_threshold(champ.model, sets["calibration"], cost)
    decisions = champ_mod.decision_report(champ.model, sets["test"], thresholds, cost)
    importance = champ_mod.feature_importance(champ.model, sets["test"], cfg)
    held_out = pd.concat([sets["calibration"], sets["test"]])
    with mlflow.start_run(run_id=champ.run_id):
        version = register_champion(champ.model_uri, cfg.registry_model_name)
        extra = {"registry_name": cfg.registry_model_name, "version": version, "alias": "champion",
                 "mlflow_run_id": champ.run_id, "reference_sha256": reference_hash()}  # fmt: skip
        summary = champ_mod.profile_summary(champ, held_out, thresholds, importance, extra)
        profile = build_profile(load_partition("reference"), pd.Series(
            champ_mod.score(champ.model, held_out)), summary)  # fmt: skip
        mlflow.log_artifact(str(write_profile(profile, PROFILE_PATH)))
        flat = {f"{k}_{m}": v for k, d in decisions.items() for m, v in d.items()}
        mlflow.log_metrics({f"test_{k}": v for k, v in flat.items()})
    return {
        "version": version,
        "thresholds": thresholds,
        "decisions": decisions,
        "importance": importance,
        "profile_path": str(PROFILE_PATH.relative_to(PROJECT_ROOT).as_posix()),
    }


def record(result: CandidateResult, cfg: TrainingConfig, champion_info: dict | None) -> None:
    """Write the RUN record of one candidate."""
    is_champ = champion_info is not None
    verdict = "champion (v{})".format(champion_info["version"]) if is_champ else "candidato"
    extra = {"Calibração": result.calibration, "Brier calib_select": json.dumps(result.briers),
             "PSI do score (test → OOT)": json.dumps({k: round(v, 4) for k, v in
                                                      result.score_psi.items()})}  # fmt: skip
    if is_champ:
        extra |= {"Limiar (valor esperado)": champion_info["thresholds"]["threshold"],
                  "Limiar (F1)": champion_info["thresholds"]["threshold_f1"],
                  "Decisão no test": json.dumps(champion_info["decisions"])}  # fmt: skip
    rec = RunRecord(
        run_id=next_run_id("train", "REF"), kind="train", scenario="REF", seed=cfg.seed,
        data_hash=reference_hash(), model=result.name,
        mlflow_ref=f"training / {result.run_id}", metrics=result.metrics, verdict=verdict,
        artifacts=["mlflow: model"] + ([champion_info["profile_path"]] if is_champ else []),
        extra=extra,
    )  # fmt: skip
    write_record(rec)


def main() -> None:
    """Train every configured candidate, select and register the champion, write records."""
    settings = get_settings()
    configure_logging(settings.log_level)
    cfg = load_training_config()
    setup_tracking("training")
    sets = prepare_sets(cfg)
    results = [fit_candidate(name, sets, cfg) for name in cfg.models]
    champ = select_champion(results, cfg)
    info = finalize(champ, sets, cfg)
    for result in results:
        record(result, cfg, info if result is champ else None)
    logger.info("training finished", extra={"champion": champ.name, "version": info["version"]})


if __name__ == "__main__":
    main()
