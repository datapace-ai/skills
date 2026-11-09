"""Summarise what a datapace-collector bundle holds, without printing any row.

Usage: uv run --no-project python -I scripts/bundle_summary.py <bundle.tgz>

Prints the provider, each input's status, and counts: database resources,
daily cost rows and the days they cover, metric series, the resources they
cover and the days with data. Reads manifest.json, inventory.json, costs.json
and metrics.json from the bundle; aliases.json sits outside the bundle and is
never read.
"""

import json
import sys
import tarfile
from datetime import datetime, timedelta


def load(tar: tarfile.TarFile, name: str) -> dict:
    try:
        member = tar.extractfile(name)
    except KeyError:
        return {}
    return json.load(member) if member else {}


def summary(path: str) -> dict:
    with tarfile.open(path, "r:gz") as tar:
        manifest = load(tar, "manifest.json")
        inventory = load(tar, "inventory.json")
        costs = load(tar, "costs.json")
        metrics = load(tar, "metrics.json")
    # Azure adds sql_databases and managed_instances, Google Cloud alloydb.
    databases = sum(len(v) for v in inventory.values() if isinstance(v, list))
    daily = costs.get("daily", [])
    cost_days = sorted({r["date"] for r in daily if r.get("date")})
    series = metrics.get("series", [])
    metric_days = set()
    for s in series:
        start = datetime.fromisoformat(s["start"].replace("Z", "+00:00"))
        period = s.get("period", 3600)
        for i, v in enumerate(s.get("values", [])):
            if v is not None:
                metric_days.add((start + timedelta(seconds=i * period)).date())
    return {
        "provider": manifest.get("provider"),
        "inputs": {k: v.get("status") for k, v in manifest.get("inputs", {}).items()},
        "databases": databases,
        "cost_rows": len(daily),
        "cost_days": len(cost_days),
        "cost_range": [cost_days[0], cost_days[-1]] if cost_days else None,
        "metric_series": len(series),
        "metric_resources": len({s.get("alias") for s in series}),
        "metric_days": len(metric_days),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: bundle_summary.py <bundle.tgz>")
    print(json.dumps(summary(sys.argv[1]), indent=2))
