"""``make screenshots``: PNG evidence of the dashboard via Grafana's render API (no login).

Renders the full dashboard and each panel for one scenario over the last ``minutes``.
Files go to ``docs/evidence/observability/`` (aggregates only: the panels plot gauges).
"""

import argparse
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from src.config import PROJECT_ROOT
from src.observability.dashboard import dashboard

GRAFANA = "http://127.0.0.1:3000"
OUT = PROJECT_ROOT / "docs" / "evidence" / "observability"
UID = "cdm-monitoring"


def slug(title: str) -> str:
    """File-friendly panel name."""
    ascii_ = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    keep = "".join(c if c.isalnum() else "_" for c in ascii_)
    return "_".join(p for p in keep.split("_") if p)[:40]


def render(path: str, params: dict[str, str], out: Path) -> Path:
    """GET a Grafana render URL and save the PNG."""
    url = f"{GRAFANA}/render/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=120) as resp:  # local Grafana only
        out.write_bytes(resp.read())
    return out


def main(argv: list[str] | None = None) -> int:
    """Render the dashboard and every panel of one scenario."""
    p = argparse.ArgumentParser(description="Render dashboard evidence.")
    p.add_argument("--scenario", default="S1")
    p.add_argument("--minutes", type=int, default=15)
    args = p.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    base = {"orgId": "1", "from": f"now-{args.minutes}m", "to": "now",
            "var-scenario": args.scenario, "tz": "America/Sao_Paulo"}  # fmt: skip
    render(f"d/{UID}/x", {**base, "width": "1600", "height": "1850", "kiosk": "true"},
           OUT / f"{args.scenario}_dashboard.png")  # fmt: skip
    for panel in dashboard()["panels"][5:]:
        params = {**base, "panelId": str(panel["id"]), "width": "1200", "height": "450"}
        render(f"d-solo/{UID}/x", params, OUT / f"{args.scenario}_{slug(panel['title'])}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
