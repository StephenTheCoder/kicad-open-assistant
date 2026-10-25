"""CI-only check of the managed-host container; synthetic accounting, no API call."""
import os
from pathlib import Path
import sqlite3
import sys
from kicad_open_assistant.service.ledger import Ledger

assert os.geteuid() == 10001
status = Path("/proc/1/status").read_text()
assert "Uid:\t10001\t10001\t10001\t10001" in status
assert "Gid:\t10001\t10001\t10001\t10001" in status
assert Path("/data").is_mount()
ledger = Ledger(os.environ["KOA_LEDGER"])
assert ledger.path == Path("/data/koa/ledger.sqlite3")
assert ledger.path.stat().st_uid == 10001
if sys.argv[1:] == ["prepare-restart"]:
    ledger.configure(1000, True)
    ledger.issue("restart-fixture", 900)
    ledger.reserve("restart-fixture", "synthetic-reservation", 300)
    ledger.settle("restart-fixture", "synthetic-reservation", 100)
    ledger.kill()
elif sys.argv[1:] == ["verify-restart"]:
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT enabled,budget FROM control").fetchone() == (0, 1000)
        assert db.execute("SELECT charge,state FROM requests WHERE id='synthetic-reservation'").fetchone() == (100, "settled")
    assert ledger.status("restart-fixture")["remaining_microdollars"] == 800
else:
    raise SystemExit("Specify a restart check phase.")
print("Managed-host container: non-root HTTP process and persistent accounting check PASS.")
