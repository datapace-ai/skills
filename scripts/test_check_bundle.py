"""Self-check for assess/scripts/check_bundle.py on synthetic bundles.

Run: python3 -I scripts/test_check_bundle.py
"""

import hashlib
import importlib.util
import io
import json
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cb", ROOT / "assess/scripts/check_bundle.py")
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

START = "2026-10-10T00:00:00Z"
HOURS = 30 * 24


def series(alias, metric, present=HOURS):
    return {"alias": alias, "metric": metric, "statistic": "Average", "period": 3600,
            "start": START, "values": [None] * (HOURS - present) + [1.0] * present}


def azure(**over):
    """A good Azure bundle: one PostgreSQL flexible server, 30 days of metrics, spend."""
    docs = {
        "inventory.json": {"resources": [{"alias": "srv_a", "engine": "postgresql"}],
                           "sql_databases": [], "managed_instances": []},
        "metrics.json": {"series": [series("srv_a", "cpu_percent"), series("srv_a", "active_connections")]},
        "costs.json": {"daily": [{"date": "2026-10-01", "account": "acct_x", "resource_alias": "srv_a",
                                  "amount": 1.0, "currency": "EUR"}]},
        "reservations.json": {"reservations": []},
    }
    docs.update(over)
    inputs = {n: {"status": "complete", "reason_code": None}
              for n in ("inventory", "metrics", "costs", "reservations")}
    return docs, inputs


def write(tmp, docs, inputs, provider="azure", tamper=None, aliases=None):
    raw = {n: json.dumps(d).encode() for n, d in docs.items()}
    manifest = {"provider": provider, "inputs": inputs, "windows": {"metric_days": 30},
                "artifacts": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
                              for n, b in raw.items()]}
    if tamper:
        raw[tamper] += b" "
    path = Path(tmp) / f"b{len(list(Path(tmp).glob('*.tgz')))}.tgz"
    with tarfile.open(path, "w:gz") as tar:
        for name, data in {"manifest.json": json.dumps(manifest).encode(), **raw}.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    (Path(tmp) / "aliases.json").write_text(json.dumps(aliases or {"salt": "00", "aliases": {}}))
    return path


def codes(result):
    return sorted(f["code"] for f in result["findings"])


with tempfile.TemporaryDirectory() as tmp:
    good = cb.check(write(tmp, *azure()), {"postgresql": 1})
    assert good["verdict"] == "good" and good["findings"] == [], good

    empty_spend = cb.check(write(tmp, *azure(**{"costs.json": {"daily": []}})), {})
    assert empty_spend["verdict"] == "good_with_gaps" and codes(empty_spend) == ["spend_empty"], empty_spend

    young = {"series": [series("srv_a", "cpu_percent", 10 * 24), series("srv_a", "active_connections", 10 * 24)]}
    short = cb.check(write(tmp, *azure(**{"metrics.json": young})), {})
    assert codes(short) == ["metrics_short"] and short["findings"][0]["rerun_after_days"] == 4, short

    docs, inputs = azure(**{"inventory.json": {"resources": []}, "metrics.json": {"series": []}})
    missing = cb.check(write(tmp, docs, inputs), {"postgresql": 1})
    assert missing["verdict"] == "bad" and codes(missing) == ["inventory_missing"], missing

    gcp_docs = {"inventory.json": {"resources": [], "alloydb": []}, "metrics.json": {"series": []},
                "costs.json": {"daily": [{"date": "2026-11-01", "sku_description": "Cloud SQL for PostgreSQL",
                                          "currency": "CAD"}]}}
    gcp_inputs = {"inventory": {"status": "partial", "reason_code": "not_enabled"},
                  "metrics": {"status": "complete"}, "costs": {"status": "complete"}}
    quota = cb.check(write(tmp, gcp_docs, gcp_inputs, provider="gcp"), {})
    assert quota["verdict"] == "bad" and quota["findings"][0]["action"] == "user_command", quota

    tampered = cb.check(write(tmp, *azure(), tamper="costs.json"), {})
    assert tampered["verdict"] == "bad" and "hash_mismatch" in codes(tampered), tampered

    leak_docs, leak_inputs = azure(**{"costs.json": {"daily": [
        {"date": "2026-10-01", "resource_alias": "srv_a", "amount": 1.0, "currency": "EUR",
         "note": "prod-orders-db"}]}})
    aliases = {"salt": "00", "aliases": {"srv_a": {"identifier": "prod-orders-db", "account": "sub-1"}}}
    leak = cb.check(write(tmp, leak_docs, leak_inputs, aliases=aliases), {})
    assert leak["verdict"] == "bad" and codes(leak) == ["raw_identifier"], leak
    assert "prod-orders-db" not in json.dumps(leak), leak

print("check_bundle ok")
