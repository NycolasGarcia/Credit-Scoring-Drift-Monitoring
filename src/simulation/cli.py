"""``make simulate``: generate scenario batches, pass each through the gate, persist everything.

Per scenario, under ``data/simulated/<id>/``: one folder per batch with ``applications``,
``labels`` and ``scored`` parquet files, plus ``manifest.json``. The aggregate manifest is
also copied to ``docs/evidence/scenarios/<id>.json``.
"""

import argparse
import json
import logging
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np

from src.config import PROJECT_ROOT, get_settings
from src.contracts.gate import GateContext, run_gate
from src.contracts.settings import load_contract_config
from src.data.features import model_feature_columns
from src.data.split import content_hash
from src.logging_config import configure_logging
from src.models.dataset import load_partition
from src.models.registry import load_alias, setup_tracking
from src.models.settings import load_training_config
from src.reporting.run_record import git_state, write_record
from src.simulation.engine import SimBatch, SimContext, simulate
from src.simulation.manifest import batch_summary, build_manifest, dumps
from src.simulation.natural import natural_batches
from src.simulation.record import build_record
from src.simulation.settings import ScenarioConfig, load_scenario, scenario_ids

logger = logging.getLogger(__name__)
PROFILE_PATH = PROJECT_ROOT / "models" / "reference_profile.json"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "scenarios"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """CLI arguments."""
    parser = argparse.ArgumentParser(description="Generate and score degradation scenarios.")
    parser.add_argument("--scenario", default="all", help="scenario id (S0..S5) or 'all'")
    parser.add_argument("--no-record", action="store_true", help="skip RUN records (debug runs)")
    return parser.parse_args(argv)


def gate_context(profile: dict[str, Any]) -> GateContext:
    """Champion, threshold and contract, as used in production."""
    setup_tracking("training")
    model = load_alias(load_training_config().registry_model_name)
    version = f"credit-scoring@champion v{profile['model']['version']}"
    root = get_settings().data_dir / "quarantine"
    return GateContext(model, profile["threshold"], version, profile, load_contract_config(), root)


def batches_for(cfg: ScenarioConfig, ctx: GateContext) -> tuple[Iterator[SimBatch], str]:
    """Batch iterator and content hash of the base partition."""
    if cfg.source == "production":
        prod = load_partition("production")
        return natural_batches(cfg, prod), content_hash(prod)
    base = load_partition("holdout")
    cols = model_feature_columns()

    def risk(df):
        return np.asarray(ctx.model.predict_proba(df[cols])[:, 1], dtype=float)

    return simulate(SimContext(cfg, base, ctx.profile, risk)), content_hash(base)


def persist(batch: SimBatch, scored, folder: Path) -> None:
    """Write applications, labels and scored rows of one batch (local only, git-ignored)."""
    folder.mkdir(parents=True, exist_ok=True)
    batch.applications.to_parquet(folder / "applications.parquet", index=False)
    batch.labels.to_parquet(folder / "labels.parquet", index=False)
    scored.to_parquet(folder / "scored.parquet", index=False)


def scenario_dir(scenario_id: str) -> Path:
    """Local (git-ignored) folder of one scenario's batches."""
    return get_settings().data_dir / "simulated" / scenario_id


def run_scenario(cfg: ScenarioConfig, ctx: GateContext) -> dict[str, Any]:
    """Generate, gate, score and persist every batch; return the manifest."""
    out_dir = scenario_dir(cfg.id)
    shutil.rmtree(out_dir, ignore_errors=True)
    batches, base_hash = batches_for(cfg, ctx)
    summaries = []
    for batch in batches:
        outcome = run_gate(batch.applications, batch.batch_id, ctx)
        persist(batch, outcome.scored, out_dir / batch.batch_id)
        summaries.append(batch_summary(batch, outcome))
        logger.info("scenario batch", extra={k: summaries[-1][k] for k in
                    ("batch_id", "intensity", "rows", "gate_status", "rows_scored")})  # fmt: skip
    model = {"version": ctx.version, "threshold": ctx.threshold}
    manifest = build_manifest(cfg, base_hash, model, summaries)
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    configure_logging(get_settings().log_level)
    args = parse_args(argv)
    ids = scenario_ids() if args.scenario == "all" else [args.scenario]
    git = git_state()
    ctx = gate_context(json.loads(PROFILE_PATH.read_text(encoding="utf-8")))
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    for sid in ids:
        cfg = load_scenario(sid)
        manifest = run_scenario(cfg, ctx)
        if not args.no_record:
            manifest["run_id"] = write_record(build_record(cfg, manifest, git)).stem
        for path in (EVIDENCE_DIR / f"{sid}.json", scenario_dir(sid) / "manifest.json"):
            path.write_text(dumps(manifest), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
