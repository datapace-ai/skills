"""Check a datapace-collector bundle against references/bundle-check.md.

Usage:
  uv run --no-project python -I scripts/check_bundle.py <bundle.tgz> [--expect ENGINE=N ...]

--expect is what discovery counted in scope, per engine key (bundle-check.md).
aliases.json beside the bundle is read for the privacy check only; its content
is never printed, nor is any row of the bundle. Prints one JSON verdict:
`good`, `good_with_gaps` or `bad`, with counts and findings. Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import tarfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# From datapace-platform, src/datapace/domain/assessment/rules/series.py.
MIN_SPAN_DAYS = 14
MIN_SAMPLE_PERCENT = 80
# The upload limit (collector bundle.py WARN_BYTES, the upload's 64 MiB cap).
MAX_BYTES = 64 * 2**20

# The metrics each provider's `idle` rule reads, per inventory list; a tuple
# is alternatives (datapace-platform rules: utilisation.py, azure/utilisation.py,
# azure/sql_database.py, azure/managed_instance.py, gcp/utilisation.py, gcp/alloydb.py).
CORE = {
    ("aws", "resources"): [("CPUUtilization",), ("DatabaseConnections",)],
    ("azure", "resources"): [("cpu_percent",), ("active_connections",)],
    ("azure", "sql_databases"): [("cpu_percent", "dtu_consumption_percent"), ("sessions_count",)],
    ("azure", "managed_instances"): [("avg_cpu_percent",)],
    ("gcp", "resources"): [
        ("database/cpu/utilization",),
        ("database/postgresql/num_backends", "database/network/connections"),
    ],
    ("gcp", "alloydb"): [("instance/cpu/average_utilization",), ("instance/postgres/total_connections",)],
}

# reason_code -> action; see bundle-check.md "Fix loop".
ACTION = {
    "access_denied": "grant",
    "not_enabled": "grant",
    "throttled": "rerun",
    "service_error": "rerun",
    "cancelled": "rerun",
    "not_selected": "explain",
}


def engine_key(provider: str, kind: str, record: dict) -> str:
    if kind == "sql_databases":
        return "sql_database"
    if kind == "managed_instances":
        return "sql_managed_instance"
    if kind == "alloydb":
        return "alloydb"
    engine = str(record.get("engine", "")).lower()
    return engine.split("_")[0] if provider == "gcp" else engine


def span_days(values: list, start: datetime, period: int) -> tuple[float, int]:
    """Span from the first to the last present sample, and the present count (series.py)."""
    present = [i for i, v in enumerate(values) if v is not None]
    if not present:
        return 0.0, 0
    hours = (present[-1] - present[0]) * period // 3600 + 1
    return hours / 24, len(present)


def check(path: Path, expect: dict[str, int], aliases: Path | None = None) -> dict:
    findings: list[dict] = []

    def add(check: str, severity: str, code: str, detail: str, action: str, **extra) -> None:
        findings.append({"check": check, "severity": severity, "code": code,
                         "detail": detail, "action": action, **extra})

    size = path.stat().st_size
    try:
        with tarfile.open(path, "r:gz") as tar:
            raw = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
        manifest = json.loads(raw["manifest.json"])
    except (OSError, tarfile.TarError, KeyError, ValueError) as exc:
        add("integrity", "bad", "unreadable", f"bundle or manifest unreadable ({type(exc).__name__})", "rerun")
        return {"verdict": "bad", "bundle": path.name, "bytes": size, "findings": findings}

    provider = manifest.get("provider") or "aws"  # schema v1 bundles were AWS only
    inputs = {k: v or {} for k, v in manifest.get("inputs", {}).items()}

    # Integrity.
    if size > MAX_BYTES:
        add("integrity", "bad", "too_large", f"{size} bytes, over the 64 MiB upload limit", "rerun_smaller")
    for art in manifest.get("artifacts", []):
        data = raw.get(art.get("name"))
        if data is None:
            add("integrity", "bad", "artifact_missing", f"{art.get('name')} listed but absent", "rerun")
        elif hashlib.sha256(data).hexdigest() != art.get("sha256") or len(data) != art.get("bytes"):
            add("integrity", "bad", "hash_mismatch", f"{art.get('name')} does not match its sha256", "rerun")
    docs = {}
    for name in ("inventory.json", "costs.json", "metrics.json", "reservations.json"):
        try:
            docs[name] = json.loads(raw[name]) if name in raw else {}
        except ValueError:
            docs[name] = {}
            add("integrity", "bad", "artifact_unparsable", f"{name} is not JSON", "rerun")

    def status(name: str) -> tuple[str, str | None]:
        inp = inputs.get(name, {})
        return inp.get("status", "absent"), inp.get("reason_code")

    # Inventory.
    resources = []  # (alias, kind, engine)
    for kind, rows in docs["inventory.json"].items():
        if isinstance(rows, list):
            resources += [(r.get("alias"), kind, engine_key(provider, kind, r)) for r in rows]
    by_engine = Counter(e for _, _, e in resources)
    inv_status, inv_reason = status("inventory")
    costs = docs["costs.json"].get("daily", [])
    # GCP billing rows name the service; a Cloud SQL or AlloyDB line means a database exists.
    billed_db = provider == "gcp" and any(
        str(r.get("sku_description", "")).startswith(("Cloud SQL", "AlloyDB")) for r in costs)
    for engine, n in sorted(expect.items()):
        if by_engine[engine] < n:
            add("inventory", "bad", "inventory_missing",
                f"{by_engine[engine]} of {n} {engine} found by discovery",
                "user_command" if provider == "gcp" and inv_reason == "not_enabled" else
                ACTION.get(inv_reason, "fix_flags"), reason_code=inv_reason)
    if not resources and not expect:
        hint = "user_command" if billed_db and inv_reason == "not_enabled" else ACTION.get(inv_reason, "fix_flags")
        add("inventory", "bad", "no_databases",
            "no database in the bundle" + (" while billing shows Cloud SQL or AlloyDB spend" if billed_db else ""),
            hint, reason_code=inv_reason)
    elif inv_status != "complete" and not any(f["check"] == "inventory" for f in findings):
        add("inventory", "gap", "inventory_partial", f"inventory {inv_status}",
            ACTION.get(inv_reason, "explain"), reason_code=inv_reason)

    # Metrics.
    series = docs["metrics.json"].get("series", [])
    met_status, met_reason = status("metrics")
    window = int(manifest.get("windows", {}).get("metric_days", 30))
    per_alias = defaultdict(dict)
    for s in series:
        start = datetime.fromisoformat(str(s.get("start", "")).replace("Z", "+00:00"))
        got = span_days(s.get("values", []), start, int(s.get("period", 3600)))
        have = per_alias[s.get("alias")]
        have[s.get("metric")] = max(got, have.get(s.get("metric"), (0.0, 0)))
    metric_days = []
    if resources and not series:
        add("metrics", "bad", "metrics_missing",
            f"no metric series for {len(resources)} databases (metrics {met_status})",
            ACTION.get(met_reason, "rerun"), reason_code=met_reason)
    elif resources:
        lacking, short, sparse = 0, [], 0
        for alias, kind, _ in resources:
            have = per_alias.get(alias, {})
            spans = []
            for alternatives in CORE.get((provider, kind), []):
                found = [have[m] for m in alternatives if m in have]
                if not found:
                    spans = None
                    break
                spans.append(max(found))
            if spans is None:
                lacking += 1
                continue
            span = min(s for s, _ in spans)
            metric_days.append(span)
            if span < MIN_SPAN_DAYS:
                short.append(span)
            elif min(c for _, c in spans) * 100 < MIN_SAMPLE_PERCENT * window * 24:
                sparse += 1
        if lacking:
            add("metrics", "gap", "core_metrics_missing",
                f"{lacking} of {len(resources)} databases lack a core metric (metrics {met_status})",
                ACTION.get(met_reason, "explain"), reason_code=met_reason)
        if short:
            add("metrics", "gap", "metrics_short",
                f"{len(short)} databases have under {MIN_SPAN_DAYS} days of metrics",
                "wait", rerun_after_days=math.ceil(MIN_SPAN_DAYS - min(short)))
        if sparse:
            add("metrics", "gap", "metrics_sparse",
                f"{sparse} databases have under {MIN_SAMPLE_PERCENT} % of hourly samples", "explain")

    # Spend.
    cost_status, cost_reason = status("costs")
    days = sorted({r["date"] for r in costs if r.get("date")})
    currencies = sorted({r.get("currency") or r.get("unit") for r in costs} - {None, ""})
    if resources and not costs:
        code = "spend_list_price" if provider == "gcp" and cost_reason == "not_selected" else "spend_empty"
        add("spend", "gap", code,
            f"no cost rows for {len(resources)} databases (costs {cost_status})",
            ACTION.get(cost_reason, "explain"), reason_code=cost_reason)
    elif provider == "azure" and costs:
        billed = {r.get("resource_alias") for r in costs}
        unbilled = sum(1 for a, kind, _ in resources if kind == "resources" and a not in billed)
        if unbilled:
            add("spend", "gap", "spend_unmatched", f"{unbilled} servers have no cost row", "explain")
    if costs and cost_status != "complete":
        add("spend", "gap", "spend_partial", f"costs {cost_status}", ACTION.get(cost_reason, "explain"),
            reason_code=cost_reason)

    # Commitments.
    for name in ("reservations", "coverage"):
        st, reason = status(name)
        if name in inputs and st != "complete" and resources:
            add("commitments", "gap", f"{name}_{st}", f"{name} {st}", ACTION.get(reason, "explain"),
                reason_code=reason)

    # Privacy: no raw id or name the aliases stand for appears in the bundle.
    aliases = aliases or path.parent / "aliases.json"
    if aliases.exists():
        try:
            entries = json.loads(aliases.read_text()).get("aliases", {}).values()
            raws = {v for e in entries for k, v in e.items() if k in ("account", "identifier")}
            raws = {r for r in raws if isinstance(r, str) and len(r) >= 4}
            text = b"\n".join(raw.values()).decode("utf-8", "replace")
            leaks = sum(1 for r in raws if r in text)
            if leaks:
                add("privacy", "bad", "raw_identifier", f"{leaks} raw ids or names appear in the bundle", "report")
        except (OSError, ValueError, AttributeError):
            add("privacy", "gap", "aliases_unreadable", "aliases.json unreadable; privacy not checked", "explain")

    severities = {f["severity"] for f in findings}
    verdict = "bad" if "bad" in severities else "good_with_gaps" if findings else "good"
    return {
        "verdict": verdict,
        "bundle": path.name,
        "bytes": size,
        "provider": provider,
        "collector_version": manifest.get("collector_version"),
        "inputs": {k: v.get("status") for k, v in inputs.items()},
        "counts": {
            "databases": dict(sorted(by_engine.items())),
            "metric_series": len(series),
            "databases_with_metrics": sum(1 for a, _, _ in resources if a in per_alias),
            "min_metric_days": round(min(metric_days), 1) if metric_days else 0,
            "cost_rows": len(costs),
            "cost_days": len(days),
            "cost_range": [days[0], days[-1]] if days else None,
            "currencies": currencies,
        },
        "findings": findings,
    }


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    expect = {}
    rest = argv[1:]
    while rest:
        flag, value, rest = rest[0], rest[1] if len(rest) > 1 else "", rest[2:]
        if flag != "--expect" or "=" not in value:
            print(__doc__, file=sys.stderr)
            return 2
        engine, n = value.split("=", 1)
        expect[engine.lower()] = expect.get(engine.lower(), 0) + int(n)
    result = check(Path(argv[0]), expect)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
