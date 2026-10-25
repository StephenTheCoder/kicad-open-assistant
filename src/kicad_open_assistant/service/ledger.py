"""Single-host SQLite ledger with serialized, durable spend reservations.

Never automatically refund an unknown outcome. Do not use this DB on NFS or
replicate it into independently writable instances.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import secrets
import sqlite3
import time
from ..policy import AppError


class Ledger:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def transaction(self):
        db = None
        try:
            db = sqlite3.connect(self.path, timeout=3, isolation_level=None)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.execute("COMMIT")
        except sqlite3.Error:
            if db and db.in_transaction:
                db.execute("ROLLBACK")
            raise AppError("accounting", "Accounting unavailable; requests disabled.") from None
        except BaseException:
            if db and db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            if db:
                db.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.executescript("""
              PRAGMA journal_mode=WAL;
              CREATE TABLE IF NOT EXISTS control(id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL, budget INTEGER NOT NULL);
              INSERT OR IGNORE INTO control VALUES(1,0,0);
              CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, allowance INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
              CREATE TABLE IF NOT EXISTS requests(user_id TEXT NOT NULL, id TEXT NOT NULL, created REAL NOT NULL,
                  charge INTEGER NOT NULL, reserved INTEGER NOT NULL, state TEXT NOT NULL,
                  PRIMARY KEY(user_id,id));
              CREATE TABLE IF NOT EXISTS attempts(bucket TEXT PRIMARY KEY, start REAL NOT NULL, count INTEGER NOT NULL);
            """)

    def configure(self, budget, enabled):
        if type(budget) is not int or budget < 0:
            raise ValueError("Budget is a nonnegative integer in microdollars.")
        with self.transaction() as db:
            db.execute("UPDATE control SET budget=?,enabled=? WHERE id=1", (budget, int(enabled)))

    def kill(self):
        with self.transaction() as db:
            db.execute("UPDATE control SET enabled=0 WHERE id=1")

    def issue(self, user_id, allowance):
        if not user_id or len(user_id) > 100 or type(allowance) is not int or allowance < 0:
            raise ValueError("Invalid user or allowance.")
        token = secrets.token_urlsafe(48)
        with self.transaction() as db:
            # Rotation retains the user's ledger and does not replenish allowance.
            db.execute("INSERT INTO users VALUES(?,?,?,0) ON CONFLICT(id) DO UPDATE SET token_hash=excluded.token_hash,allowance=excluded.allowance,revoked=0",
                       (user_id, hashlib.sha256(token.encode()).hexdigest(), allowance))
        return token

    def revoke(self, user_id):
        with self.transaction() as db:
            db.execute("UPDATE users SET revoked=1 WHERE id=?", (user_id,))

    def authenticate(self, token):
        if not isinstance(token, str) or not 32 <= len(token) <= 512:
            raise AppError("authentication", "Authentication required.")
        with self.transaction() as db:
            row = db.execute("SELECT * FROM users WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if not row:
                raise AppError("authentication", "Authentication required.")
            if row["revoked"]:
                raise AppError("revoked", "Access revoked.")
            return row["id"]

    def attempt(self, bucket, maximum=60):
        now = time.time()
        with self.transaction() as db:
            db.execute("DELETE FROM attempts WHERE start<?", (now - 120,))
            row = db.execute("SELECT * FROM attempts WHERE bucket=?", (bucket,)).fetchone()
            if row and row["start"] >= now - 60:
                if row["count"] >= maximum:
                    raise AppError("rate", "Rate limited.")
                db.execute("UPDATE attempts SET count=count+1 WHERE bucket=?", (bucket,))
            else:
                db.execute("INSERT OR REPLACE INTO attempts VALUES(?,?,1)", (bucket, now))

    def status(self, user_id):
        with self.transaction() as db:
            control = db.execute("SELECT * FROM control WHERE id=1").fetchone()
            user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not control or not user or user["revoked"]:
                raise AppError("revoked", "Access revoked.")
            used = db.execute("SELECT COALESCE(SUM(charge),0) FROM requests").fetchone()[0]
            own = db.execute("SELECT COALESCE(SUM(charge),0) FROM requests WHERE user_id=?", (user_id,)).fetchone()[0]
            return {"enabled": bool(control["enabled"]), "remaining_microdollars": max(0, min(control["budget"] - used, user["allowance"] - own))}

    def reserve(self, user_id, request_id, amount, user_concurrency=1, global_concurrency=4, per_minute=6):
        if type(amount) is not int or amount <= 0:
            raise AppError("configuration", "Invalid reservation.")
        with self.transaction() as db:
            control = db.execute("SELECT * FROM control WHERE id=1").fetchone()
            user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not control or not control["enabled"]:
                raise AppError("disabled", "Sponsored access disabled.")
            if not user or user["revoked"]:
                raise AppError("revoked", "Access revoked.")
            if db.execute("SELECT 1 FROM requests WHERE user_id=? AND id=?", (user_id, request_id)).fetchone():
                raise AppError("duplicate", "Request already accepted; no replay.")
            active = db.execute("SELECT COUNT(*) FROM requests WHERE state='reserved'").fetchone()[0]
            own_active = db.execute("SELECT COUNT(*) FROM requests WHERE user_id=? AND state='reserved'", (user_id,)).fetchone()[0]
            if active >= global_concurrency or own_active >= user_concurrency:
                raise AppError("concurrency", "Concurrency limit reached.")
            recent = db.execute("SELECT COUNT(*) FROM requests WHERE user_id=? AND created>?", (user_id, time.time() - 60)).fetchone()[0]
            if recent >= per_minute:
                raise AppError("rate", "Request rate exceeded.")
            used = db.execute("SELECT COALESCE(SUM(charge),0) FROM requests").fetchone()[0]
            own = db.execute("SELECT COALESCE(SUM(charge),0) FROM requests WHERE user_id=?", (user_id,)).fetchone()[0]
            if used + amount > control["budget"]:
                raise AppError("budget", "Global allowance exhausted.")
            if own + amount > user["allowance"]:
                raise AppError("quota", "User allowance exhausted.")
            db.execute("INSERT INTO requests VALUES(?,?,?,?,?,'reserved')", (user_id, request_id, time.time(), amount, amount))

    def settle(self, user_id, request_id, actual=None):
        with self.transaction() as db:
            row = db.execute("SELECT * FROM requests WHERE user_id=? AND id=?", (user_id, request_id)).fetchone()
            if not row or row["state"] != "reserved":
                return
            if actual is None:
                db.execute("UPDATE requests SET state='unknown' WHERE user_id=? AND id=?", (user_id, request_id))
                return
            if type(actual) is not int or actual < 0:
                raise AppError("accounting", "Invalid usage accounting.")
            # Unexpected prices/usage stop new work and retain the actual debt.
            if actual > row["reserved"]:
                db.execute("UPDATE control SET enabled=0 WHERE id=1")
            db.execute("UPDATE requests SET charge=?,state='settled' WHERE user_id=? AND id=?", (actual, user_id, request_id))
