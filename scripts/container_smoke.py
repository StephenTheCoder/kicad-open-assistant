"""Run inside the actual disabled service container; no inference or provider key."""
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from kicad_open_assistant.policy import DEFAULT_MODEL, make_request
from kicad_open_assistant.service.ledger import Ledger

ledger = Ledger(os.environ.get("KOA_LEDGER", "/data/ledger.sqlite3"))
ledger.initialize()
token = ledger.issue("container-smoke", 0)

def call(path, data=None, authenticate=False):
    headers = {"Content-Type": "application/json"}
    if authenticate:
        headers.update({"Authorization": "Bearer " + token, "Idempotency-Key": uuid.uuid4().hex})
    req = urllib.request.Request("http://127.0.0.1:8000" + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)

for _ in range(30):
    try:
        status, health = call("/healthz")
        break
    except (OSError, TimeoutError):
        time.sleep(0.5)
else:
    raise SystemExit("Container HTTP server did not start")
assert status == 200 and health["sponsored_configured"] is False
assert call("/v1/status")[0] == 401
status, allowance = call("/v1/status", authenticate=True)
assert status == 200 and allowance["enabled"] is False and allowance["remaining_microdollars"] == 0
status, result = call("/v1/chat", make_request(DEFAULT_MODEL, "Container smoke; must remain disabled", [], []), True)
assert status == 503 and result == {"error": "disabled"}
ledger.revoke("container-smoke")
assert call("/v1/status", authenticate=True)[0] == 403
assert token.encode() not in ledger.path.read_bytes()
print("Actual container HTTP smoke: health, authentication, disabled policy, revocation and secret exclusion PASS; zero inference calls.")
