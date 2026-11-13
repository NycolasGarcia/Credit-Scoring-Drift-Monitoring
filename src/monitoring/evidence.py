"""Evidence of a detection run: Evidently report on the alert window, cross-check, RUN record.

The report window is chosen by the detector itself (from the first alert on; the last batches
when nothing alerts), never by the ground truth.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from src.data.features import CATEGORICAL_FEATURES, model_feature_columns
from src.monitoring.detect import Batch
from src.monitoring.drift import feature_psi
from src.monitoring.evidently_report import build_report, column_values, save_html
from src.monitoring.output import score_psi
from src.reporting.run_record import RunRecord, next_run_id

QUIET_WINDOW = 6
MAX_ROWS = 50_000
SEED = 11


def alert_window(results: list[dict[str, Any]]) -> list[int]:
    """Batch indexes from the first SEV-1+ on (or the last ``QUIET_WINDOW`` if none)."""
    first = next((r["index"] for r in results if r["severity"]["level"] >= 1), None)
    if first is None:
        return [r["index"] for r in results][-QUIET_WINDOW:]
    return [r["index"] for r in results if r["index"] >= first]


def pooled_current(batches: list[Batch], window: list[int]) -> pd.DataFrame:
    """Scored rows of the window with their features (sampled to ``MAX_ROWS``)."""
    parts = [b.applications.merge(b.scored[["loan_key", "score"]], on="loan_key")
             for b in batches if b.index in window]  # fmt: skip
    pooled = pd.concat(parts, ignore_index=True)
    return pooled.sample(min(len(pooled), MAX_ROWS), random_state=SEED)


def cross_check(values: dict[str, float], current: pd.DataFrame, profile: dict) -> list[dict]:
    """Evidently ``psi_ref`` vs. the project's PSI, per column (nulls explain any gap)."""
    rows = []
    for col, ev in values.items():
        own = (score_psi(current[col], profile) if col == "score"
               else feature_psi(current[col], profile["features"][col]))  # fmt: skip
        rows.append({"column": col, "evidently": round(ev, 6), "own": round(own, 6),
                     "abs_diff": round(abs(ev - own), 6),
                     "null_share": round(float(current[col].isna().mean()), 4)})  # fmt: skip
    return sorted(rows, key=lambda r: -r["evidently"])


def evidently_section(
    reference: pd.DataFrame, current: pd.DataFrame, profile: dict, threshold: float, html: Path
) -> dict[str, Any]:
    """Run the report, save the HTML and return the drifted columns plus the cross-check."""
    numeric = [c for c in model_feature_columns() if c not in CATEGORICAL_FEATURES] + ["score"]
    snapshot = build_report(reference, current, numeric, list(CATEGORICAL_FEATURES), threshold)
    save_html(snapshot, html)
    values = column_values(snapshot)
    flagged = sorted((c for c, v in values.items() if v >= threshold), key=lambda c: -values[c])
    return {"html": html.name, "rows_current": len(current), "rows_reference": len(reference),
            "threshold": threshold, "drifted_columns": flagged,
            "cross_check": cross_check(values, current, profile)}  # fmt: skip


def _verdict(ev: dict[str, Any]) -> str:
    diag = ev["diagnosis"]
    top = max(diag["counts"], key=diag["counts"].get) if diag["counts"] else "none"
    return (f"1º alerta: lote {ev['first_sev1']} (atraso {ev['delay_sev1']}) · camadas "
            f"{'/'.join(ev['layers_fired']) or '—'} · diagnóstico dominante {top} "
            f"(esperado {diag['expected']})")  # fmt: skip


def detection_record(
    sid: str, ev: dict[str, Any], meta: dict[str, Any], git: tuple[str, bool]
) -> RunRecord:
    """RUN record (kind ``monitor``) of one scenario's detection and evaluation."""
    att, fa = ev["attribution"], ev["false_alarm"]
    metrics = {"detector": {
        "falso alarme SEV-1+": fa["sev1_plus"], "falso alarme SEV-2+": fa["sev2_plus"],
        "lotes pós-onset SEV-1+": ev["post_onset"]["sev1_plus"],
        "atraso SEV-1 (lotes)": ev["delay_sev1"], "atraso SEV-2 (lotes)": ev["delay_sev2"],
        "recall de atribuição": att["recall"], "precisão de atribuição": att["precision"],
        "acurácia do diagnóstico": ev["diagnosis"]["accuracy"]}}  # fmt: skip
    return RunRecord(
        run_id=next_run_id("monitor", sid), kind="monitor", scenario=sid, seed=SEED,
        data_hash=meta["base_sha256"], model=meta["model"], mlflow_ref="—", metrics=metrics,
        verdict=_verdict(ev), sha=git[0], dirty=git[1],
        artifacts=[f"docs/evidence/drift/{sid}.json", f"docs/evidence/drift/{sid}_evidently.html"],
        extra={"limiares": meta["thresholds"], "simulação": meta["sim_run"]},
    )  # fmt: skip
