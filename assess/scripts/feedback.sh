#!/bin/sh
# Send one anonymous feedback report to Datapace (references/feedback.md).
# Usage: feedback.sh '<json body without skillVersion>' [bundle.tgz]
set -eu

if [ "${DATAPACE_SKILL_NO_FEEDBACK:-}" = "1" ]; then
  echo "feedback off (DATAPACE_SKILL_NO_FEEDBACK=1); nothing sent"
  exit 0
fi

body=${1:?usage: feedback.sh '<json body>' [bundle.tgz]}
case "$body" in
  "{"*) ;;
  *) echo "feedback.sh: the body must be a JSON object" >&2; exit 2 ;;
esac

# A last guard behind the agent's scrubbing: AWS account ids, Azure GUIDs, ARNs, home paths.
if printf '%s' "$body" | grep -Eiq '[0-9]{12}|[0-9a-f]{8}-[0-9a-f]{4}-|arn:|/(Users|home)/'; then
  echo "feedback.sh: the body looks like it carries an identifier; scrub it and retry" >&2
  exit 2
fi

dir=$(cd "$(dirname "$0")/.." && pwd)
version=$(sed -n 's/^ *version: *"\([^"]*\)".*/\1/p' "$dir/SKILL.md" | head -n 1)
url=${DATAPACE_FEEDBACK_URL:-https://assessment-api-1005032345308.northamerica-northeast1.run.app/api/v1/agent-feedback}
body="{\"skillVersion\":\"$version\",${body#?}"

# With a bundle, add collectorVersion and inputs from its manifest.json: a version
# string and status/reason enums per input, nothing that can name the user.
if [ -n "${2:-}" ]; then
  full=$(uv run --no-project python -I -c '
import json, sys, tarfile
body = json.loads(sys.argv[1])
with tarfile.open(sys.argv[2]) as t:
    m = json.load(t.extractfile("manifest.json"))
body["collectorVersion"] = m["collector_version"]
body["inputs"] = {k: {"status": v["status"], "reasonCode": v.get("reason_code")}
                  for k, v in m.get("inputs", {}).items() if v}
print(json.dumps(body))
' "$body" "$2") && body=$full || echo "feedback.sh: manifest unreadable; sending without it" >&2
fi

curl -sS -o /dev/null -w '%{http_code}\n' --max-time 20 \
  -X POST "$url" -H 'Content-Type: application/json' \
  --data "$body"
