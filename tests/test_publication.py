"""Prove that the publication guard blocks forbidden files and messages."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_publication as cp  # noqa: E402

BAIT_STRING = "bait-token-7f3a"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Fresh git repo with a local denylist containing a bait path and string."""
    _git(tmp_path, "init", "-q")
    (tmp_path / ".git" / "info" / "publish-denylist").write_text(
        f"path:secret_notes.md\npath:.private/**\nstring:{BAIT_STRING}\n", encoding="utf-8"
    )
    return tmp_path


def _stage(repo: Path, rel: str, content: str | bytes) -> list[str]:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode() if isinstance(content, str) else content
    target.write_bytes(data)
    _git(repo, "add", "-f", rel)
    return cp.run(cp.parse_args(["--staged", "--repo", str(repo)]))


@pytest.mark.parametrize("rel", ["src/module.py", "src/data/load.py", "src/models/train.py"])
def test_clean_source_file_passes(repo: Path, rel: str) -> None:
    assert _stage(repo, rel, "x = 1\n") == []


@pytest.mark.parametrize(
    "rel",
    [
        "secret_notes.md",
        ".private/settings.json",
        "data/raw/loans.csv",
        ".env",
        "models/model.pkl",
        "mlruns/0/meta.yaml",
        "kaggle.json",
        "export.parquet",
    ],
)
def test_forbidden_paths_are_blocked(repo: Path, rel: str) -> None:
    assert _stage(repo, rel, "content\n")


def test_fixture_csv_and_env_example_are_allowed(repo: Path) -> None:
    assert _stage(repo, "tests/fixtures/synthetic.csv", "a,b\n1,2\n") == []
    assert _stage(repo, ".env.example", "KEY=<placeholder>\n") == []


def test_denylisted_string_is_blocked(repo: Path) -> None:
    assert _stage(repo, "docs/note.md", f"made with {BAIT_STRING.upper()}\n")


def test_private_key_is_blocked(repo: Path) -> None:
    header = "-----BEGIN RSA PRIVATE" + " KEY-----"
    assert _stage(repo, "src/k.py", f"{header}\nabc\n")


def test_large_file_is_blocked(repo: Path) -> None:
    assert _stage(repo, "src/big.txt", b"0" * (cp.MAX_BYTES + 1))


def test_row_level_evidence_html_is_blocked(repo: Path) -> None:
    html = "<table>" + "<tr><td>1</td></tr>" * (cp.MAX_EVIDENCE_TABLE_ROWS + 1) + "</table>"
    assert _stage(repo, "docs/evidence/report.html", html)


@pytest.mark.parametrize(
    ("msg", "ok"),
    [
        ("feat(data): adiciona loader", True),
        ("docs: atualiza readme", True),
        ("wip", False),
        ("Adiciona coisa", False),
        (f"fix: corrige\n\n{BAIT_STRING}", False),
    ],
)
def test_commit_message_rules(repo: Path, msg: str, ok: bool) -> None:
    assert (cp.check_commit_message(msg, cp.load_denylist(repo)) == []) is ok


def test_history_scan_finds_committed_bait(repo: Path) -> None:
    _git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        f"chore: {BAIT_STRING}",
    )
    assert cp.check_history(repo, cp.load_denylist(repo))
