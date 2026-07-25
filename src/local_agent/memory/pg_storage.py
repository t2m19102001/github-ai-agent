"""
PostgreSQL persistence for agent sessions.

Same contract as SessionStore (storage.py) — ensure_session / append_turn /
load_turns with (role, content) Turn objects — but backed by Postgres instead
of a local SQLite file. Use this when the agent should share a real database
with the rest of the stack (the web surface already speaks Postgres), or when
several processes may read/write sessions concurrently.

Connection: pass a libpq DSN / URL, e.g.
    postgresql://postgres@localhost/local_agent

Each call opens a short-lived connection (open → work → close) so no handle is
held between turns; fine for a CLI. A pool can be added later if needed.
"""

from __future__ import annotations

import psycopg2

from src.local_agent.memory.storage import Turn

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS turns (
    id         BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
"""


class PostgresSessionStore:
    """Store/read conversation turns in PostgreSQL (SessionStore-compatible)."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg2.connect(self.dsn)

    def _init_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(_SCHEMA)

    def ensure_session(self, session_id: str, *, now: str) -> None:
        """Create the session row if absent (idempotent)."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions(session_id, created_at) VALUES (%s, %s) "
                "ON CONFLICT (session_id) DO NOTHING",
                (session_id, now),
            )

    def append_turn(self, session_id: str, turn: Turn, *, now: str) -> None:
        """Record one turn, creating the session row first if needed."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions(session_id, created_at) VALUES (%s, %s) "
                "ON CONFLICT (session_id) DO NOTHING",
                (session_id, now),
            )
            cur.execute(
                "INSERT INTO turns(session_id, role, content, created_at) "
                "VALUES (%s, %s, %s, %s)",
                (session_id, turn.role, turn.content, now),
            )

    def load_turns(self, session_id: str, *, limit: int | None = None) -> list[Turn]:
        """Return this session's turns oldest-first (optionally the last N)."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT role, content FROM turns WHERE session_id = %s "
                "ORDER BY id ASC",
                (session_id,),
            )
            rows = cur.fetchall()
        turns = [Turn(role=r, content=c) for r, c in rows]
        if limit is not None and limit >= 0:
            return turns[-limit:]
        return turns


__all__ = ["PostgresSessionStore"]
