"""Check that the assess skill still matches the published datapace-collector.

Installs the version pinned in assess/references/collector.md from PyPI into a
temporary venv, then fails if:
- assess/references/iam-policy.json does not grant exactly the collector's
  READ_ONLY_OPERATIONS, or
- assess/references/coverage.md marks a provider `available` that the
  collector's `--provider` cannot collect, or
- a role the collector's Azure or Google Cloud preflight names is missing from
  the role lists in assess/references/collector.md.

COLLECTOR_SPEC overrides what is installed, e.g. a local wheel to check a
release before it is on PyPI: COLLECTOR_SPEC='/path/x.whl[azure,gcp]'.

Stdlib only. Run: python3 -I scripts/check_drift.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

REFS = Path(__file__).resolve().parent.parent / "assess" / "references"
PROVIDERS = {"AWS": "aws", "Azure": "azure", "Google Cloud": "gcp"}

PROBE = """
import contextlib, importlib.util, inspect, io, json, re

def roles():
    out = {}
    if importlib.util.find_spec("datapace_collector.azure"):
        from datapace_collector.azure.preflight import ROLES
        out["azure"] = sorted({role for role, _ in ROLES.values()})
    if importlib.util.find_spec("datapace_collector.gcp"):
        from datapace_collector.gcp import preflight
        out["gcp"] = sorted(set(re.findall(r"roles/[A-Za-z.]+", inspect.getsource(preflight))))
    return out

from datapace_collector.operations import READ_ONLY_OPERATIONS
from datapace_collector import cli
out = io.StringIO()
with contextlib.redirect_stdout(out):
    try:
        cli.main(["--help"])
    except SystemExit:
        pass
m = __import__("re").search(r"--provider \\{([a-z,]+)\\}", out.getvalue())
print(json.dumps({
    "actions": sorted(f"{s}:{o}" for s, o in READ_ONLY_OPERATIONS),
    "providers": m.group(1).split(",") if m else ["aws"],
    "roles": roles(),
}))
"""


def pinned_version() -> str:
    m = re.search(r"^Pinned version: (\S+)$", (REFS / "collector.md").read_text(), re.M)
    if not m:
        sys.exit("collector.md: no 'Pinned version: X' line")
    return m.group(1)


def collector_facts(version: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        venv.create(tmp, with_pip=True)
        py = Path(tmp) / "bin" / "python"
        subprocess.run(
            [py, "-m", "pip", "install", "-q", "--disable-pip-version-check",
             os.environ.get("COLLECTOR_SPEC") or f"datapace-collector[azure,gcp]=={version}"],
            check=True,
        )
        out = subprocess.run([py, "-I", "-c", PROBE], check=True, capture_output=True, text=True)
        return json.loads(out.stdout)


def documented_roles() -> dict[str, set[str]]:
    text = (REFS / "collector.md").read_text()
    out = {}
    for provider, label in (("azure", "Azure roles:"), ("gcp", "Google Cloud roles:")):
        line = next((l for l in text.splitlines() if l.lstrip("- ").startswith(label)), "")
        out[provider] = set(re.findall(r"`([^`]+)`", line))
    return out


def policy_actions() -> list[str]:
    policy = json.loads((REFS / "iam-policy.json").read_text())
    return sorted(a for st in policy["Statement"] for a in st["Action"])


def available_providers() -> set[str]:
    found = set()
    for line in (REFS / "coverage.md").read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] in PROVIDERS and cells[2].startswith("available"):
            found.add(PROVIDERS[cells[0]])
    return found


def main() -> int:
    version = pinned_version()
    facts = collector_facts(version)
    errors = []
    policy = policy_actions()
    if policy != facts["actions"]:
        missing = sorted(set(facts["actions"]) - set(policy))
        extra = sorted(set(policy) - set(facts["actions"]))
        errors.append(f"iam-policy.json differs from {version}: missing {missing}, extra {extra}")
    unsupported = sorted(available_providers() - set(facts["providers"]))
    if unsupported:
        errors.append(f"coverage.md marks {unsupported} available; {version} collects {facts['providers']}")
    documented = documented_roles()
    for provider, roles in facts["roles"].items():
        missing = sorted(set(roles) - documented[provider])
        if missing:
            errors.append(f"collector.md {provider} roles lack {missing} named by {version}")
    for e in errors:
        print(f"drift: {e}", file=sys.stderr)
    if not errors:
        print(f"no drift against datapace-collector {version}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
