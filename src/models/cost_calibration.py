"""Cost calibration and FP/FN validation job (``make cost``, ADR-0016).

1. Estimate LGD and interest realization (good and bad loans) from realized cash on TRAIN.
2. For the configured premises and for the freshly estimated ones (same funding rate), choose
   the value-maximizing threshold on the CALIBRATION split.
3. Validate on the TEST split against what each decision actually returned (realized cash net
   of funding): modeled vs. realized curve, regret of the chosen threshold, FP/FN money.
"""

import json
import logging

import numpy as np
import pandas as pd

from src.config import PROJECT_ROOT, get_settings
from src.logging_config import configure_logging
from src.models.dataset import internal_split, load_partition, xy
from src.models.economics import (
    confusion_costs,
    estimate_premises,
    net_of_funding,
    read_cost_frame,
    realized_economics,
    realized_value,
)
from src.models.registry import load_alias, setup_tracking
from src.models.settings import CostConfig, load_cost_config, load_training_config
from src.models.threshold import (
    best_value_threshold,
    expected_value,
    loan_economics,
    threshold_grid,
)
from src.reporting.run_record import RunRecord, git_state, next_run_id, write_record

logger = logging.getLogger(__name__)
EVIDENCE = PROJECT_ROOT / "docs" / "evidence" / "models" / "cost_validation.json"
ESTIMATED_KEYS = ("lgd", "margin_realization", "bad_interest_realization")


def attach_economics(sets: dict[str, pd.DataFrame], econ: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Join realized economics to each split by ``loan_key`` (every loan must match)."""
    cols = ["loan_key", "net_cash", "funded_amnt", "total_rec_int", "contractual_interest",
            "loss_rate", "interest_realization"]  # fmt: skip
    # int_rate comes from the partition itself (origination feature)
    out = {}
    for name, df in sets.items():
        joined = df.merge(econ[cols], on="loan_key", how="left", validate="one_to_one")
        if joined["net_cash"].isna().any():
            raise ValueError(f"{name}: loans without realized economics")
        out[name] = joined
    return out


def curves(df: pd.DataFrame, p: np.ndarray, cost: CostConfig) -> pd.DataFrame:
    """Modeled (premise-based) and realized value per application across the grid."""
    _, y = xy(df)
    gain, loss = loan_economics(df, cost)
    net = net_of_funding(df, cost.funding_rate)
    rows = [{"threshold": t, "modeled": expected_value(y.to_numpy(), p, gain, loss, t),
             "realized": realized_value(net, p, t)} for t in threshold_grid(cost)]  # fmt: skip
    return pd.DataFrame(rows)


def validate(test: pd.DataFrame, p: np.ndarray, cost: CostConfig, t_chosen: float) -> dict:
    """Regret, curve agreement and FP/FN money of the chosen threshold on held-out data."""
    c = curves(test, p, cost)
    best = c.loc[c["realized"].idxmax()]
    chosen = float(c.loc[np.isclose(c["threshold"], t_chosen), "realized"].iloc[0])
    y = xy(test)[1].to_numpy()
    return {
        "realized_optimal_threshold": float(best["threshold"]),
        "realized_value_at_optimal": float(best["realized"]),
        "realized_value_at_chosen": chosen,
        "regret_pct": float((best["realized"] - chosen) / best["realized"] * 100),
        "curve_pearson": float(np.corrcoef(c["modeled"], c["realized"])[0, 1]),
        "confusion_at_chosen": confusion_costs(
            y, p, net_of_funding(test, cost.funding_rate), t_chosen
        ),
    }


def run(cfg, base_cost: CostConfig) -> dict:
    """Execute the calibration and return every aggregate for evidence and the RUN record."""
    settings = get_settings()
    key = settings.pseudonymization_key.get_secret_value()
    econ = realized_economics(read_cost_frame(settings.raw_data_path, key))
    sets = attach_economics(internal_split(load_partition("reference"), cfg), econ)
    premises = estimate_premises(sets["train"])
    estimated = base_cost.model_copy(update={k: premises[k] for k in ESTIMATED_KEYS})
    setup_tracking("training")
    model = load_alias(cfg.registry_model_name)
    p = {k: np.asarray(model.predict_proba(xy(sets[k])[0])[:, 1]) for k in ("calibration", "test")}
    y_cal = xy(sets["calibration"])[1].to_numpy()
    out = {"premises_train": premises}
    for label, cost in (("configured", base_cost), ("estimated", estimated)):
        gain, loss = loan_economics(sets["calibration"], cost)
        t, _ = best_value_threshold(y_cal, p["calibration"], gain, loss, threshold_grid(cost))
        out[label] = {**{k: getattr(cost, k) for k in (*ESTIMATED_KEYS, "funding_rate")},
                      "threshold": t, **validate(sets["test"], p["test"], cost, t)}  # fmt: skip
    out["funding_sensitivity"] = funding_sensitivity(sets["test"], p["test"], base_cost)
    return out


def funding_sensitivity(test: pd.DataFrame, p: np.ndarray, cost: CostConfig) -> list[dict]:
    """Realized-cash optimal threshold and approval rate for each funding rate (test set)."""
    rows = []
    for rate in cost.funding_rate_grid:
        net = net_of_funding(test, rate)
        values = [(t, realized_value(net, p, t)) for t in threshold_grid(cost)]
        t_best, v_best = max(values, key=lambda tv: tv[1])
        rows.append({"funding_rate": rate, "realized_optimal_threshold": float(t_best),
                     "approval_rate": float(np.mean(p < t_best)), "value_per_app": v_best,
                     "value_approve_all": realized_value(net, p, 1.01)})  # fmt: skip
    return rows


def record(result: dict, cfg, git: tuple[str, bool]) -> None:
    """RUN record of the cost calibration."""
    metrics = {
        label: {k: v for k, v in result[label].items() if isinstance(v, float)}
        for label in ("configured", "estimated")
    }
    metrics["premissas (train)"] = {k: float(v) for k, v in result["premises_train"].items()}
    extra = {f"Matriz FP/FN no teste ({k})": json.dumps(result[k]["confusion_at_chosen"])
             for k in ("configured", "estimated")}  # fmt: skip
    extra["Sensibilidade ao custo de funding (teste, caixa realizado)"] = json.dumps(
        [{k: round(v, 4) for k, v in row.items()} for row in result["funding_sensitivity"]]
    )
    write_record(RunRecord(
        run_id=next_run_id("calib", "COST"), kind="calib", scenario="COST", seed=cfg.seed,
        data_hash=_reference_hash(), model=f"{cfg.registry_model_name}@champion",
        mlflow_ref="—", metrics=metrics, verdict=_verdict(result),
        artifacts=[EVIDENCE.relative_to(PROJECT_ROOT).as_posix()], extra=extra,
        sha=git[0], dirty=git[1],
    ))  # fmt: skip


def _verdict(result: dict) -> str:
    c, e = result["configured"], result["estimated"]
    head = f"config: limiar {c['threshold']:.3f}, regret {c['regret_pct']:.2f}%"
    est = (f"estimado: LGD {e['lgd']:.3f}, margem {e['margin_realization']:.3f}, "
           f"juros dos maus {e['bad_interest_realization']:.3f}")  # fmt: skip
    return f"{head} · {est} · funding {c['funding_rate']:.0%}"


def _reference_hash() -> str:
    manifest = get_settings().data_dir / "processed" / "split_manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["partitions"]["reference"][
        "content_sha256"
    ]


def main() -> None:
    """Run the cost calibration, write evidence and the RUN record."""
    configure_logging(get_settings().log_level)
    git = git_state()
    cfg = load_training_config()
    result = run(cfg, load_cost_config())
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    record(result, cfg, git)
    logger.info("cost calibration finished", extra={"verdict": _verdict(result)})


if __name__ == "__main__":
    main()
