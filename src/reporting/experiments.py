"""Generate ``docs/EXPERIMENTS.md`` from the MLflow ``training`` experiment (``make report``).

Every row links to the RUN record that cites the same MLflow run, so each number is
traceable without opening MLflow.
"""

import mlflow
import pandas as pd
from mlflow import MlflowClient

from src.config import PROJECT_ROOT
from src.models.registry import CHAMPION, setup_tracking
from src.models.settings import load_training_config
from src.reporting.run_record import RUNS_DIR

DOC = PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
COLUMNS = {
    "metrics.cv_train_auc": "AUC CV",
    "metrics.test_auc": "AUC test",
    "metrics.test_gini": "Gini test",
    "metrics.test_ks": "KS test",
    "metrics.test_pr_auc": "PR-AUC test",
    "metrics.test_raw_brier": "Brier pré",
    "metrics.test_brier": "Brier pós",
    "metrics.oot_2014_auc": "AUC OOT14",
    "metrics.oot_2015_auc": "AUC OOT15",
    "metrics.oot_2015_bad_rate_expected": "BR esp. OOT15",
    "metrics.oot_2015_bad_rate_observed": "BR obs. OOT15",
    "metrics.score_psi_oot_2015": "PSI score OOT15",
}
HEADER = """# Experimentos de treino

> Gerado por `make report` (`src/reporting/experiments.py`) a partir do experimento MLflow
> `training`. Não editar à mão. Cada linha aponta para o RUN record que contém o mesmo run.

Legenda: CV = validação cruzada estratificada no train; test = 15% da referência 2013 nunca
vista no treino; OOT14/OOT15 = safras 2014/2015 maduras (fora do tempo); Brier pré/pós =
antes/depois da calibração; BR = bad rate esperado (média do score) e observado; PSI score =
estabilidade da distribuição do score (bins do test).

"""


def record_for(run_id: str) -> str:
    """RUN record file citing ``run_id``, as a Markdown link (or '—')."""
    for path in sorted(RUNS_DIR.glob("RUN-*.md")):
        if run_id in path.read_text(encoding="utf-8"):
            return f"[{path.stem}](runs/{path.name})"
    return "—"


def champion_run_id() -> str | None:
    """MLflow run id behind the ``champion`` alias, if registered."""
    name = load_training_config().registry_model_name
    try:
        return MlflowClient().get_model_version_by_alias(name, CHAMPION).run_id
    except mlflow.exceptions.MlflowException:
        return None


def build_table(runs: pd.DataFrame, champ: str | None) -> str:
    """Markdown table, one row per run, newest first."""
    lines = ["| RUN | Modelo | Calibração | " + " | ".join(COLUMNS.values()) + " |",
             "|---|---|---|" + "---|" * len(COLUMNS)]  # fmt: skip
    for _, row in runs.iterrows():
        name = row["tags.mlflow.runName"] + (" **(champion)**" if row["run_id"] == champ else "")
        values = [_fmt(row.get(col)) for col in COLUMNS]
        calib = row.get("params.calibration", "—")
        lines.append(
            f"| {record_for(row['run_id'])} | {name} | {calib} | " + " | ".join(values) + " |"
        )
    return "\n".join(lines)


def _fmt(value) -> str:
    return "—" if value is None or pd.isna(value) else f"{float(value):.4f}"


def main() -> None:
    """Write the experiments document."""
    setup_tracking("training")
    runs = mlflow.search_runs(experiment_names=["training"], order_by=["start_time DESC"])
    body = build_table(runs, champion_run_id()) if len(runs) else "_Nenhum run registrado._"
    DOC.write_text(HEADER + body + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
