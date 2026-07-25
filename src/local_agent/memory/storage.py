"""
SQLite persistence for agent sessions — memory that survives process restarts.

`SessionContext` (session.py) holds a conversation in RAM; this module writes it
to a small SQLite file so a later `agent --session <id>` run can pick the
conversation back up.

Schema (two tables):
    sessions(session_id PK, created_at)
    turns(id PK, session_id FK, role, content, created_at)

We deliberately store *turns* (role + text) rather than the richer QueryRecord:
the tool-calling loop only needs "what was said before" to stay coherent, and a
flat turn log is the simplest thing that works and is easy to inspect.

All access goes through short-lived connections (open → do work → close) so
there is no long-held handle and the store is safe to use from the CLI.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS turns (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
"""


@dataclass(frozen=True)
class Turn:
    """One line of the conversation: a user question or an agent answer."""

    role: str  # "user" | "agent"
    content: str


class SessionStore:
    """Create/read conversation turns in a SQLite file."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def ensure_session(self, session_id: str, *, now: str) -> None:
        """Create the session row if it does not exist yet (idempotent)."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions(session_id, created_at) "
                "VALUES (?, ?)",
                (session_id, now),
            )

    def append_turn(self, session_id: str, turn: Turn, *, now: str) -> None:
        """Record one conversation turn, creating the session row if needed."""
        with self._connect() as conn:
            # Self-heal the FK parent so callers can append without a separate
            # ensure_session() call — one less ordering pitfall.
            conn.execute(
                "INSERT OR IGNORE INTO sessions(session_id, created_at) "
                "VALUES (?, ?)",
                (session_id, now),
            )
            conn.execute(
                "INSERT INTO turns(session_id, role, content, created_at) "
                "VALUES (?, ?, ?, ?)",
                (session_id, turn.role, turn.content, now),
            )

    def load_turns(self, session_id: str, *, limit: int | None = None) -> list[Turn]:
        """Return this session's turns oldest-first (optionally the last N)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM turns WHERE session_id = ? "
                "ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        turns = [Turn(role=r, content=c) for r, c in rows]
        if limit is not None and limit >= 0:
            return turns[-limit:]
        return turns


__all__ = ["SessionStore", "Turn"]
