"""Publication guard: block forbidden paths, secrets and denylisted content.

Modes:
    --staged            check files staged for commit (pre-commit hook, default)
    --all               check every tracked file (CI)
    --commit-msg FILE   check a commit message (commit-msg hook)
    --history           scan the whole git history (pre-push / release audit)

A local, never-versioned denylist at ``.git/info/publish-denylist`` adds
project-specific forbidden paths (``path:<glob>``) and strings (``string:<txt>``).
"""

import argparse
import fnmatch
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAX_BYTES = 1_000_000
SIZE_ALLOWLIST = ("docs/evidence/",)
MAX_EVIDENCE_TABLE_ROWS = 200
GENERIC_FORBIDDEN_PATHS = (
    "data/*",
    "models/*",
    "mlruns/*",
    "mlartifacts/*",
    "logs/*",
    "reports/*",
    ".env",
    "kaggle.json",
    "*.pem",
    "*.key",
    "*.parquet",
    "*.csv",
    "*.pkl",
    "*.joblib",
)
FIXTURE_PREFIX = "tests/fixtures/"
SECRET_PATTERNS = (
    re.compile("-----BEGIN [A-Z ]*PRIVATE" + " KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\"key\"\s*:\s*\"[0-9a-f]{32}\""),
)
COMMIT_RE = re.compile(
    r"^(feat|fix|refactor|test|docs|chore|ci|build|perf|style|revert)(\([\w\-./]+\))?!?: \S.*"
)
PII_COLUMNS_FILE = Path("config/governance/pii_columns.txt")


@dataclass
class Denylist:
    """Project-specific forbidden paths and strings."""

    paths: list[str] = field(default_factory=list)
    strings: list[str] = field(default_factory=list)


def git(repo: Path, *args: str) -> str:
    """Run a git command in ``repo`` and return stdout as text."""
    out = subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)
    return out.stdout.decode("utf-8", errors="replace")


def load_denylist(repo: Path) -> Denylist:
    """Read ``.git/info/publish-denylist`` if present."""
    deny = Denylist()
    file = repo / ".git" / "info" / "publish-denylist"
    if not file.exists():
        return deny
    for raw in file.read_text(encoding="utf-8").splitlines():
        kind, _, value = raw.strip().partition(":")
        if kind == "path" and value:
            deny.paths.append(value)
        elif kind == "string" and value:
            deny.strings.append(value.lower())
    return deny


def path_violation(path: str, deny: Denylist) -> str | None:
    """Return a reason if ``path`` must never be published."""
    if any(fnmatch.fnmatch(path, pat) for pat in deny.paths):
        return "path in local denylist"
    if path == ".env.example" or path.startswith(FIXTURE_PREFIX):
        return None
    if any(fnmatch.fnmatch(path, pat) for pat in GENERIC_FORBIDDEN_PATHS):
        return "forbidden path pattern (data/artifact/secret)"
    return None


def content_violations(text: str, deny: Denylist) -> list[str]:
    """Return reasons found in a text blob (denylisted strings, secrets)."""
    lowered = text.lower()
    reasons = [f"denylisted string #{i}" for i, s in enumerate(deny.strings) if s in lowered]
    reasons += ["secret-like pattern" for p in SECRET_PATTERNS if p.search(text)]
    return reasons


def evidence_violations(path: str, text: str, pii_columns: list[str]) -> list[str]:
    """Flag row-level tables or PII columns inside published HTML evidence."""
    if not (path.startswith("docs/evidence/") and path.endswith(".html")):
        return []
    reasons = []
    if text.lower().count("<tr") > MAX_EVIDENCE_TABLE_ROWS:
        reasons.append("evidence HTML contains a row-level table")
    reasons += [f"evidence mentions PII column '{c}'" for c in pii_columns if c in text]
    return reasons


def load_pii_columns(repo: Path) -> list[str]:
    """Read the PII column list maintained alongside the data inventory."""
    file = repo / PII_COLUMNS_FILE
    if not file.exists():
        return []
    return [ln.strip() for ln in file.read_text(encoding="utf-8").splitlines() if ln.strip()]


def check_file(repo: Path, path: str, blob: bytes, deny: Denylist) -> list[str]:
    """Run every per-file check and return prefixed reasons."""
    reasons = []
    if reason := path_violation(path, deny):
        reasons.append(reason)
    if len(blob) > MAX_BYTES and not path.startswith(SIZE_ALLOWLIST):
        reasons.append(f"file larger than {MAX_BYTES} bytes")
    text = blob.decode("utf-8", errors="ignore")
    reasons += content_violations(text, deny)
    reasons += evidence_violations(path, text, load_pii_columns(repo))
    return [f"{path}: {r}" for r in reasons]


def staged_files(repo: Path) -> list[tuple[str, bytes]]:
    """Return (path, staged content) for added/copied/modified/renamed files."""
    names = git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    paths = [p for p in names.split("\0") if p]
    blobs = [
        subprocess.run(["git", "show", f":{p}"], cwd=repo, capture_output=True, check=True).stdout
        for p in paths
    ]
    return list(zip(paths, blobs, strict=True))


def tracked_files(repo: Path) -> list[tuple[str, bytes]]:
    """Return (path, working-tree content) for every tracked file."""
    paths = [p for p in git(repo, "ls-files", "-z").split("\0") if p]
    return [(p, (repo / p).read_bytes()) for p in paths if (repo / p).is_file()]


def check_commit_message(text: str, deny: Denylist) -> list[str]:
    """Validate Conventional Commits format and denylisted strings."""
    first = text.strip().splitlines()[0] if text.strip() else ""
    reasons = (
        []
        if COMMIT_RE.match(first) or first.startswith("Merge ")
        else ["commit message is not Conventional Commits: '<type>(<scope>): <summary>'"]
    )
    body = "\n".join(ln for ln in text.splitlines() if not ln.startswith("#"))
    return reasons + [f"commit message: {r}" for r in content_violations(body, deny)]


def check_history(repo: Path, deny: Denylist) -> list[str]:
    """Scan every commit (paths, patches and messages) across all refs."""
    paths = {p for p in git(repo, "log", "--all", "--name-only", "--format=").splitlines() if p}
    reasons = [f"history path {p}: {r}" for p in sorted(paths) if (r := path_violation(p, deny))]
    patches = git(repo, "log", "--all", "-p", "--format=%H%n%B")
    return reasons + [f"history: {r}" for r in content_violations(patches, deny)]


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--all", action="store_true")
    mode.add_argument("--commit-msg", type=Path)
    mode.add_argument("--history", action="store_true")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> list[str]:
    """Dispatch to the selected mode and return all violations."""
    repo, deny = args.repo, load_denylist(args.repo)
    if args.commit_msg:
        return check_commit_message(args.commit_msg.read_text(encoding="utf-8"), deny)
    if args.history:
        return check_history(repo, deny)
    files = tracked_files(repo) if args.all else staged_files(repo)
    return [r for path, blob in files for r in check_file(repo, path, blob, deny)]


def main(argv: list[str] | None = None) -> int:
    """Entry point. Exit code 1 when any violation is found."""
    violations = run(parse_args(argv))
    for v in violations:
        sys.stderr.write(f"PUBLISH-CHECK FAIL  {v}\n")
    if not violations:
        sys.stderr.write("publish-check: OK\n")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
