"""Gate CLI: ``make validate`` (real monthly batch) and ``make validate-bad`` (injected defects).

Exit code 0 = batch scored (passed or partial); 2 = batch blocked (GR-1).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, get_settings
from src.contracts.d6 import sweep
from src.contracts.gate import EXIT_BLOCKED, GateContext, GateOutcome, run_gate
from src.contracts.schema import to_application_batch
from src.contracts.settings import load_contract_config
from src.logging_config import configure_logging
from src.models.dataset import load_partition
from src.models.registry import load_alias, setup_tracking
from src.models.settings import load_training_config
from src.simulation.bad_batch import DEFECTS, make_bad_batch

PROFILE_PATH = PROJECT_ROOT / "models" / "reference_profile.json"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "contracts"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """CLI arguments."""
    parser = argparse.ArgumentParser(description="Run the data-contract quality gate on a batch.")
    parser.add_argument(
        "--vintage", default="2014-01", help="production month to validate (YYYY-MM)"
    )
    parser.add_argument("--bad", action="store_true", help="inject defects into a holdout sample")
    parser.add_argument("--defects", default="all", help="comma-separated defect names or 'all'")
    parser.add_argument("--rate", type=float, default=0.02, help="share of rows hit by row defects")
    parser.add_argument("--rows", type=int, default=20000, help="holdout rows used for a bad batch")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--evidence", action="store_true", help="write the report to docs/evidence")
    parser.add_argument("--d6-sweep", action="store_true", help="contract vs. drift on unit bugs")
    parser.add_argument(
        "--expect-blocked", action="store_true", help="succeed only if the batch is blocked"
    )
    return parser.parse_args(argv)


def write_d6_sweep(profile: dict[str, Any], seed: int) -> Path:
    """Run the D6 sweep on the holdout and write it to docs/evidence/contracts."""
    batch = to_application_batch(load_partition("holdout"))
    rows = sweep(batch, profile, load_contract_config(), seed)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE_DIR / "d6_sweep.json"
    body = {"base": "holdout", "rows": len(batch), "seed": seed, "results": rows}
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return path


def build_batch(args: argparse.Namespace) -> tuple[str, Any, dict | None]:
    """Return (batch_id, application batch, defect manifest or None)."""
    if not args.bad:
        prod = load_partition("production")
        return (
            f"natural-{args.vintage}",
            to_application_batch(prod[prod["vintage"] == args.vintage]),
            None,
        )
    names = list(DEFECTS) if args.defects == "all" else args.defects.split(",")
    base = to_application_batch(load_partition("holdout").sample(args.rows, random_state=args.seed))
    batch, manifest = make_bad_batch(base, names, args.seed, args.rate)
    return f"bad-{args.defects.replace(',', '+')}-seed{args.seed}", batch, manifest


def gate(batch_id: str, batch, profile: dict[str, Any]) -> GateOutcome:
    """Run the gate with the registered champion and its reference profile."""
    setup_tracking("training")
    model = load_alias(load_training_config().registry_model_name)
    version = f"credit-scoring@champion v{profile['model']['version']}"
    root = get_settings().data_dir / "quarantine"
    ctx = GateContext(model, profile["threshold"], version, profile, load_contract_config(), root)
    return run_gate(batch, batch_id, ctx)


def write_evidence(outcome: GateOutcome, manifest: dict | None) -> Path:
    """Aggregate report (and defect manifest) for docs/evidence/contracts."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE_DIR / f"{outcome.report['batch_id']}.json"
    body = {**outcome.report, "rows_scored": len(outcome.scored), "exit_code": outcome.exit_code,
            "injected_defects": manifest}  # fmt: skip
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the gate exit code."""
    configure_logging(get_settings().log_level)
    args = parse_args(argv)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if args.d6_sweep:
        write_d6_sweep(profile, args.seed)
        return 0
    batch_id, batch, manifest = build_batch(args)
    outcome = gate(batch_id, batch, profile)
    if args.evidence:
        write_evidence(outcome, manifest)
    if args.expect_blocked:
        return 0 if outcome.exit_code == EXIT_BLOCKED and outcome.scored.empty else 1
    return outcome.exit_code


if __name__ == "__main__":
    sys.exit(main())
