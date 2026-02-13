"""
Shadow Database — Structured memory storage.
SQLite with chunks, todos, and feedback tables.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class ShadowDatabase:
    """Direct SQLite storage for Shadow Core — no ORM overhead."""

    def __init__(self, db_path: str = "~/shadow-memory/shadow.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_tables(self):
        conn = self._conn()
        c = conn.cursor()

        # Raw 5-second chunks
        c.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL    NOT NULL,
                text        TEXT    NOT NULL,
                audio_path  TEXT,
                intent      TEXT,
                priority    INTEGER DEFAULT 0,
                processed   INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)

        # Extracted todos with priority
        c.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id            INTEGER,
                task                TEXT    NOT NULL,
                priority            INTEGER DEFAULT 5,
                category            TEXT    DEFAULT 'other',
                status              TEXT    DEFAULT 'pending',
                deadline            TEXT,
                user_benefit_score  REAL    DEFAULT 0.0,
                workspace_path      TEXT,
                created_at          TEXT    DEFAULT (datetime('now')),
                updated_at          TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (chunk_id) REFERENCES chunks(id)
            )
        """)

        # User feedback for learning
        c.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                todo_id   INTEGER,
                action    TEXT,
                timestamp REAL,
                notes     TEXT,
                FOREIGN KEY (todo_id) REFERENCES todos(id)
            )
        """)

        # Sessions (web app sessions)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT    PRIMARY KEY,
                started_at  TEXT    NOT NULL,
                ended_at    TEXT,
                duration    INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                summary     TEXT,
                status      TEXT    DEFAULT 'active'
            )
        """)

        conn.commit()
        conn.close()

    # ── Chunks ──

    def insert_chunk(
        self,
        timestamp: float,
        text: str,
        audio_path: Optional[str] = None,
        intent: Optional[str] = None,
        priority: int = 0,
        session_id: Optional[str] = None,
    ) -> int:
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO chunks (timestamp, text, audio_path, intent, priority) VALUES (?, ?, ?, ?, ?)",
            (timestamp, text, audio_path, intent, priority),
        )
        chunk_id = c.lastrowid
        conn.commit()
        conn.close()
        return chunk_id

    def get_recent_chunks(self, limit: int = 10) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM chunks ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_chunk_intent(self, chunk_id: int, intent: str, priority: int):
        conn = self._conn()
        conn.execute(
            "UPDATE chunks SET intent=?, priority=?, processed=1 WHERE id=?",
            (intent, priority, chunk_id),
        )
        conn.commit()
        conn.close()

    # ── Todos ──

    def insert_todo(
        self,
        chunk_id: int,
        task: str,
        priority: int = 5,
        category: str = "other",
        deadline: Optional[str] = None,
    ) -> int:
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO todos (chunk_id, task, priority, category, deadline) VALUES (?, ?, ?, ?, ?)",
            (chunk_id, task, priority, category, deadline),
        )
        todo_id = c.lastrowid
        conn.commit()
        conn.close()
        return todo_id

    def get_pending_todos(self, min_priority: int = 1) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM todos WHERE status='pending' AND priority >= ? ORDER BY priority DESC",
            (min_priority,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_todos(self, limit: int = 50) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM todos ORDER BY priority DESC, created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_todo_status(self, todo_id: int, status: str):
        conn = self._conn()
        conn.execute(
            "UPDATE todos SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, todo_id),
        )
        conn.commit()
        conn.close()

    # ── Sessions ──

    def create_session(self, session_id: str):
        conn = self._conn()
        conn.execute(
            "INSERT INTO sessions (id, started_at) VALUES (?, datetime('now'))",
            (session_id,),
        )
        conn.commit()
        conn.close()

    def end_session(self, session_id: str, duration: int, chunk_count: int, summary: str):
        conn = self._conn()
        conn.execute(
            "UPDATE sessions SET ended_at=datetime('now'), duration=?, chunk_count=?, summary=?, status='ended' WHERE id=?",
            (duration, chunk_count, summary, session_id),
        )
        conn.commit()
        conn.close()

    def get_sessions(self, limit: int = 20) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── Stats ──

    def get_stats(self) -> dict:
        conn = self._conn()
        chunks = conn.execute("SELECT COUNT(*) as n FROM chunks").fetchone()["n"]
        todos = conn.execute("SELECT COUNT(*) as n FROM todos").fetchone()["n"]
        pending = conn.execute("SELECT COUNT(*) as n FROM todos WHERE status='pending'").fetchone()["n"]
        sessions = conn.execute("SELECT COUNT(*) as n FROM sessions").fetchone()["n"]
        conn.close()
        return {
            "total_chunks": chunks,
            "total_todos": todos,
            "pending_todos": pending,
            "total_sessions": sessions,
        }
