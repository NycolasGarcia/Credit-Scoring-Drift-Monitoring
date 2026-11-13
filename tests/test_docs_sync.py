"""Docs stay in sync with the code: every module and Makefile target is documented."""

import re

from src.config import PROJECT_ROOT

ARCHITECTURE = PROJECT_ROOT / "docs" / "ARCHITECTURE.md"
MAKEFILE = PROJECT_ROOT / "Makefile"


def test_architecture_lists_every_component() -> None:
    doc = ARCHITECTURE.read_text(encoding="utf-8")
    modules = [
        p.relative_to(PROJECT_ROOT).as_posix()
        for p in (PROJECT_ROOT / "src").rglob("*.py")
        if p.name != "__init__.py"
    ]
    missing = [m for m in modules if f"`{m}`" not in doc]
    assert not missing, f"undocumented modules in ARCHITECTURE.md: {missing}"


def test_make_help_lists_every_target() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    targets = set(re.findall(r"^([a-z][a-z-]*):", text, flags=re.MULTILINE)) - {"help"}
    help_block = text.split("help:", 1)[1].split("\n\n", 1)[0]
    missing = sorted(t for t in targets if t not in help_block.split())
    assert not missing, f"targets missing from make help: {missing}"
