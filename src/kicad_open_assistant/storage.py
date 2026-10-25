"""Local conversation storage; a connection per operation, transactional writes."""
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
import sys
from contextlib import contextmanager


def process_alive(pid):
    if not pid:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # Access denied: don't mislabel a live owner.
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def data_directory():
    return Path(os.environ.get("KOA_DATA_HOME") or (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "KiCadOpenAssistant"))


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_directory() / "conversations.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, title TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, conversation TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            db.execute("BEGIN IMMEDIATE")
            if "owner_pid" not in {row[1] for row in db.execute("PRAGMA table_info(messages)")}:
                db.execute("ALTER TABLE messages ADD COLUMN owner_pid INTEGER")
            db.execute("PRAGMA user_version=2")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA secure_delete=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, title="New conversation"):
        identifier = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO conversations VALUES(?,?,?)", (identifier, title[:120], time.time()))
        return identifier

    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM conversations ORDER BY created DESC")]

    def rename(self, identifier, title):
        if not title.strip():
            raise ValueError("Conversation name cannot be empty.")
        with self.connect() as db:
            db.execute("UPDATE conversations SET title=? WHERE id=?", (title.strip()[:120], identifier))

    def delete(self, identifier):
        with self.connect() as db:
            db.execute("DELETE FROM conversations WHERE id=?", (identifier,))

    def messages(self, identifier):
        with self.connect() as db:
            return [{**dict(r), "content": json.loads(r["content"])} for r in db.execute("SELECT * FROM messages WHERE conversation=? ORDER BY created,rowid", (identifier,))]

    def view(self, identifier, limit=40, budget=30 * 1024 * 1024):
        """Bound UI memory independently of total saved conversation size."""
        with self.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM messages WHERE conversation=?", (identifier,)).fetchone()[0]
            candidates = db.execute("SELECT id,length(CAST(content AS BLOB)) AS bytes FROM messages WHERE conversation=? ORDER BY created DESC,rowid DESC LIMIT ?", (identifier, limit)).fetchall()
            rows, used = [], 0
            for candidate in candidates:
                if used + candidate["bytes"] > budget:
                    break
                row = db.execute("SELECT * FROM messages WHERE id=?", (candidate["id"],)).fetchone()
                rows.append({**dict(row), "content": json.loads(row["content"])})
                used += candidate["bytes"]
            return {"messages": list(reversed(rows)), "omitted": count - len(rows)}

    def export(self, identifier, destination):
        destination = Path(destination)
        temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".partial")
        try:
            with self.connect() as db, temporary.open("x", encoding="utf-8") as output:
                output.write("[\n")
                for index, row in enumerate(db.execute("SELECT * FROM messages WHERE conversation=? ORDER BY created,rowid", (identifier,))):
                    if index:
                        output.write(",\n")
                    item = {key: row[key] for key in ("id", "role", "status", "created")}
                    item["content"] = json.loads(row["content"])
                    json.dump(item, output, ensure_ascii=False)
                output.write("\n]\n")
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def add(self, conversation, role, content, status="completed", owner_pid=None):
        identifier = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?)", (identifier, conversation, role, json.dumps(content, ensure_ascii=False), status, time.time(), owner_pid))
        return identifier

    def finish(self, identifier, text, status):
        with self.connect() as db:
            db.execute("UPDATE messages SET content=?,status=? WHERE id=?", (json.dumps([{"type": "input_text", "text": text}], ensure_ascii=False), status, identifier))

    def interrupt(self, identifier):
        with self.connect() as db:
            for row in db.execute("SELECT id,owner_pid FROM messages WHERE conversation=? AND status='streaming'", (identifier,)).fetchall():
                if not process_alive(row["owner_pid"]):
                    db.execute("UPDATE messages SET status='interrupted' WHERE id=? AND status='streaming'", (row["id"],))

    def settings(self):
        with self.connect() as db:
            return {r["key"]: json.loads(r["value"]) for r in db.execute("SELECT * FROM settings")}

    def save_settings(self, value):
        allowed = {"mode", "model", "endpoint", "output_limit", "history_count"}
        if set(value) - allowed:
            raise ValueError("Settings must not contain credentials.")
        with self.connect() as db:
            for key, item in value.items():
                db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, json.dumps(item)))
