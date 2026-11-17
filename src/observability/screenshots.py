"""``make screenshots``: PNG evidence of the dashboard via Grafana's render API (no login).

Renders the full dashboard and each panel for one scenario over the last ``minutes``.
Files go to ``docs/evidence/observability/`` (aggregates only: the panels plot gauges).
"""

import argparse
import json
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from src.config import PROJECT_ROOT
from src.observability.dashboard import dashboard

GRAFANA = "http://127.0.0.1:3000"
PROMETHEUS = "http://127.0.0.1:9090"
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


def alert_history(minutes: int) -> list[dict[str, str]]:
    """Alerts that fired in the last ``minutes``, by name, severity and scenario (Prometheus)."""
    query = f'max_over_time(ALERTS{{alertstate="firing"}}[{minutes}m])'
    url = f"{PROMETHEUS}/api/v1/query?{urllib.parse.urlencode({'query': query})}"
    with urllib.request.urlopen(url, timeout=60) as resp:  # local Prometheus only
        result = json.loads(resp.read())["data"]["result"]
    rows = [{k: r["metric"].get(k, "") for k in ("alertname", "severity", "scenario")}
            for r in result]  # fmt: skip
    return sorted(rows, key=lambda r: (r["scenario"], r["alertname"], r["severity"]))


def write_summary(minutes: int) -> Path:
    """Alert history JSON plus the alert timeline across every scenario."""
    out = OUT / "alerts_fired.json"
    body = {"window_minutes": minutes, "alerts": alert_history(minutes)}
    out.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    alerts = dashboard()["panels"][-1]
    params = {"orgId": "1", "from": f"now-{minutes}m", "to": "now", "var-scenario": "$__all",
              "panelId": str(alerts["id"]), "width": "1400", "height": "700",
              "tz": "America/Sao_Paulo"}  # fmt: skip
    render(f"d-solo/{UID}/x", params, OUT / "all_alertas_disparados.png")
    return out


def main(argv: list[str] | None = None) -> int:
    """Render the dashboard and every panel of one scenario (or the cross-scenario summary)."""
    p = argparse.ArgumentParser(description="Render dashboard evidence.")
    p.add_argument("--scenario", default="S1")
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--summary", action="store_true", help="alert history across scenarios")
    p.add_argument("--from-ms", type=int, help="absolute window start (epoch ms)")
    p.add_argument("--to-ms", type=int, help="absolute window end (epoch ms)")
    args = p.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.summary:
        write_summary(args.minutes)
        return 0
    start = str(args.from_ms) if args.from_ms else f"now-{args.minutes}m"
    end = str(args.to_ms) if args.to_ms else "now"
    base = {"orgId": "1", "from": start, "to": end, "var-scenario": args.scenario,
            "tz": "America/Sao_Paulo"}  # fmt: skip
    render(f"d/{UID}/x", {**base, "width": "1600", "height": "2150", "kiosk": "true"},
           OUT / f"{args.scenario}_dashboard.png")  # fmt: skip
    for panel in dashboard()["panels"][5:]:
        params = {**base, "panelId": str(panel["id"]), "width": "1200", "height": "450"}
        render(f"d-solo/{UID}/x", params, OUT / f"{args.scenario}_{slug(panel['title'])}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
