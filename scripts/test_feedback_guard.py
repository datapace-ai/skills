"""Self-check for the identifier guard in assess/scripts/feedback.sh.

Refused bodies must exit 2 and send nothing; the example bodies in
assess/references/feedback.md must still send. A local server stands in for
the feedback endpoint.

Run: python3 -I scripts/test_feedback_guard.py
"""

import http.server
import os
import re
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "assess/scripts/feedback.sh"
received = []


class Sink(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        received.append(self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(204)
        self.end_headers()

    def log_message(self, *_):
        pass


server = http.server.HTTPServer(("127.0.0.1", 0), Sink)
threading.Thread(target=server.serve_forever, daemon=True).start()
ENV = {**os.environ, "DATAPACE_FEEDBACK_URL": f"http://127.0.0.1:{server.server_port}/",
       "DATAPACE_RUN_IDS": "acme-prod-4821, acme-billing"}
ENV.pop("DATAPACE_SKILL_NO_FEEDBACK", None)


def run(message):
    body = message if message.startswith("{") else (
        '{"category":"blocked","step":"collect","agent":"codex","message":"%s"}' % message)
    before = len(received)
    code = subprocess.run(["sh", str(SCRIPT), body], env=ENV, capture_output=True).returncode
    return code, len(received) - before


REFUSED = {
    "email": "contact jane.doe@example.org about it",
    "aws host": "could not reach db1.abc123.us-east-1.rds.amazonaws.com",
    "azure host": "server srv.postgres.database.azure.com timed out",
    "azure storage": "blob at x.blob.core.windows.net",
    "azure mgmt": "management.azure.com returned 403",
    "gcp host": "sqladmin.googleapis.com said 403",
    "ipv4": "connection to 10.0.12.7 refused",
    "ipv4-like version": "collector 1.2.3.4",
    "windows path": r"file at C:\\Users\\jane\\out",
    "tilde path": "wrote ~/datapace-out",
    "unix path": "wrote /Users/jane/out",
    "aws account": "account 123456789012 denied",
    "guid": "subscription 0b1f6471-1bf0-4dda-aec3-111122223333",
    "arn": "arn:aws:iam::role/x",
    "run project id": "project acme-prod-4821 has no billing export",
    "run id, other case": "project ACME-BILLING denied",
}
for name, message in REFUSED.items():
    assert run(message) == (2, 0), name

examples = re.findall(r"feedback\.sh '(\{.*?\})'", (ROOT / "assess/references/feedback.md").read_text())
assert len(examples) >= 2, examples
for body in examples + ['{"category":"idea","step":"other","agent":"other","message":"collector 0.5.0 ran fine"}']:
    assert run(body) == (0, 1), body

server.shutdown()
print("feedback guard ok")
