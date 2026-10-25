"""Local conversation storage; a connection per operation, transactional writes."""
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
from contextlib import contextmanager


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
                PRAGMA user_version=1;
            """)

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

    def add(self, conversation, role, content, status="completed"):
        identifier = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (identifier, conversation, role, json.dumps(content, ensure_ascii=False), status, time.time()))
        return identifier

    def finish(self, identifier, text, status):
        with self.connect() as db:
            db.execute("UPDATE messages SET content=?,status=? WHERE id=?", (json.dumps([{"type": "input_text", "text": text}], ensure_ascii=False), status, identifier))

    def interrupt(self, identifier):
        with self.connect() as db:
            db.execute("UPDATE messages SET status='interrupted' WHERE conversation=? AND status='streaming'", (identifier,))

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
