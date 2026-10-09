"""SQLite Memory Store for JARVIS"""

import sqlite3
import os
import json
import shutil
from datetime import datetime
from pathlib import Path


class MemoryStore:
    def __init__(self, db_path=None):
        if db_path is None:
            app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            db_dir = os.path.join(app_data, "JarvisAssistant")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "memory.db")

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self.session_id = self._new_session()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS context (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def _new_session(self):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO sessions (started_at) VALUES (?)", (datetime.now().isoformat(),))
        self.conn.commit()
        return cur.lastrowid

    def add_entry(self, role, content):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
            (self.session_id, role, content)
        )
        self.conn.commit()

    def get_history(self, limit=50):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id ASC",
            (self.session_id,)
        )
        return [{"role": row["role"], "content": row["content"]} for row in cur.fetchall()[-limit:]]

    def get_session_id(self):
        return self.session_id

    def new_session(self):
        self.session_id = self._new_session()
        return self.session_id

    def save_session(self, name=None):
        if name is None:
            name = f"session_{self.session_id}"
        session_dir = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "JarvisAssistant" / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / f"{name}.json"
        history = self.get_history(limit=999999)
        data = {"session_id": self.session_id, "name": name, "history": history,
                "saved_at": datetime.now().isoformat()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(path)

    def load_session(self, name_or_path):
        session_dir = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "JarvisAssistant" / "sessions"
        path = Path(name_or_path)
        if not path.exists():
            path = session_dir / f"{name_or_path}.json"
        if not path.exists():
            return False, f"Session not found: {name_or_path}"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Create new session and import history
        self.session_id = self._new_session()
        cur = self.conn.cursor()
        for entry in data.get("history", []):
            cur.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (self.session_id, entry.get("role", "user"), entry.get("content", ""))
            )
        self.conn.commit()
        return True, f"Loaded session: {data.get('name', name_or_path)} ({len(data.get('history', []))} messages)"

    def list_sessions(self):
        session_dir = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "JarvisAssistant" / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        sessions = []
        for f in sorted(session_dir.glob("*.json"), key=os.path.getmtime, reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                sessions.append({"name": data.get("name", f.stem), "file": str(f),
                                 "messages": len(data.get("history", [])),
                                 "saved_at": data.get("saved_at", "")})
            except Exception:
                sessions.append({"name": f.stem, "file": str(f), "messages": 0, "saved_at": ""})
        return sessions

    def clear_conversation(self):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM conversations WHERE session_id = ?", (self.session_id,))
        self.conn.commit()

    def set_preference(self, key, value):
        cur = self.conn.cursor()
        cur.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    def get_preference(self, key):
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None

    def close(self):
        self.conn.close()
