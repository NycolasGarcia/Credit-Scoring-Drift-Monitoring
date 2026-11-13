"""Column inventory: the single source of truth for column roles and personal data.

The inventory lives in ``config/data/column_inventory.yaml``. Everything that needs to
know whether a column is a model feature, post-origination (leaks the label) or
personal data derives it from here.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from src.config import PROJECT_ROOT

INVENTORY_PATH = PROJECT_ROOT / "config" / "data" / "column_inventory.yaml"
PII_EXPORT_PATH = PROJECT_ROOT / "config" / "governance" / "pii_columns.txt"

Category = Literal[
    "identificador_direto", "quase_identificador", "texto_livre",
    "originacao", "pos_originacao", "alvo", "metadado",
]  # fmt: skip
Use = Literal["feature", "segmento", "alvo", "chave", "metadado", "descartado"]


class ColumnSpec(BaseModel):
    """Classification of one raw column."""

    cat: Category
    pii: Literal["direto", "quase", "nao"]
    use: Use
    why: str = ""


class Inventory(BaseModel):
    """All raw columns keyed by name."""

    columns: dict[str, ColumnSpec]

    def by_use(self, use: Use) -> list[str]:
        """Columns with the given intended use, in file order."""
        return [name for name, spec in self.columns.items() if spec.use == use]

    def by_category(self, cat: Category) -> list[str]:
        """Columns with the given category, in file order."""
        return [name for name, spec in self.columns.items() if spec.cat == cat]

    def publish_forbidden(self) -> list[str]:
        """Personal-data columns that are discarded and have unambiguous names.

        Only names containing ``_`` are exported, so that generic words (``id``,
        ``title``) do not trigger false positives in the publication guard.
        """
        return sorted(
            name
            for name, spec in self.columns.items()
            if spec.pii != "nao" and spec.use == "descartado" and "_" in name
        )


@lru_cache(maxsize=1)
def load_inventory(path: Path = INVENTORY_PATH) -> Inventory:
    """Load and validate the inventory YAML."""
    with path.open(encoding="utf-8") as fh:
        return Inventory.model_validate(yaml.safe_load(fh))


def export_pii_list(path: Path = PII_EXPORT_PATH) -> list[str]:
    """Write the publish-forbidden column list read by the publication guard."""
    names = load_inventory().publish_forbidden()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(names) + "\n", encoding="utf-8")
    return names


DOC_HEADER = """# Inventário de colunas

> Gerado por `python -m src.data.inventory` a partir de `config/data/column_inventory.yaml`.
> Não editar à mão: altere o YAML e regenere.

Legenda — **cat**: categoria do dado · **pii**: dado pessoal (LGPD) direto,
quase-identificador ou não · **use**: destino no projeto.
Nenhuma coluna é dado pessoal *sensível* (LGPD art. 5º, II).

"""


def render_markdown() -> str:
    """Render the inventory as a Markdown document with a summary and one row per column."""
    inv = load_inventory()
    counts: dict[str, int] = {}
    for spec in inv.columns.values():
        counts[spec.use] = counts.get(spec.use, 0) + 1
    summary = " · ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    rows = [f"| `{n}` | {s.cat} | {s.pii} | {s.use} | {s.why} |" for n, s in inv.columns.items()]
    table = ["| Coluna | cat | pii | use | Racional |", "|---|---|---|---|---|", *rows]
    return (
        f"{DOC_HEADER}**Total: {len(inv.columns)} colunas** — {summary}\n\n"
        + "\n".join(table)
        + "\n"
    )


if __name__ == "__main__":
    export_pii_list()
    (PROJECT_ROOT / "docs" / "data_inventory.md").write_text(render_markdown(), encoding="utf-8")
