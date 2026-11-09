"""Self-check for assess/scripts/bundle_summary.py. Run: python3 -I scripts/test_bundle_summary.py"""

import importlib.util
import io
import json
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bs", ROOT / "assess/scripts/bundle_summary.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

members = {
    "manifest.json": {"provider": "azure", "inputs": {"costs": {"status": "complete"}}},
    "inventory.json": {"resources": [{}, {}], "sql_databases": [{}], "managed_instances": []},
    "costs.json": {"daily": []},
    "metrics.json": {"series": [
        {"alias": "db-1", "start": "2026-11-01T00:00:00Z", "period": 3600,
         "values": [None] * 24 + [1.0] + [None] * 23},
        {"alias": "db-1", "start": "2026-11-01T00:00:00Z", "period": 3600, "values": [0.5]},
    ]},
}
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "b.tgz"
    with tarfile.open(path, "w:gz") as tar:
        for name, body in members.items():
            data = json.dumps(body).encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    s = bs.summary(str(path))

assert s["provider"] == "azure" and s["inputs"] == {"costs": "complete"}, s
assert s["databases"] == 3, s
assert s["cost_rows"] == 0 and s["cost_range"] is None, s
assert s["metric_series"] == 2 and s["metric_resources"] == 1 and s["metric_days"] == 2, s
print("bundle_summary ok")
