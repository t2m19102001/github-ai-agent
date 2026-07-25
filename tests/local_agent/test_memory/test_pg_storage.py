"""Tests for PostgresSessionStore.

Skipped automatically unless a reachable Postgres is configured via the
LOCAL_AGENT_TEST_PG_DSN environment variable, so the suite stays green on
machines without Postgres (e.g. CI). Each test uses a unique session id and
cleans up after itself, so it is safe against a shared database.
"""

from __future__ import annotations

import os

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 required for PG tests")

from src.local_agent.memory.storage import Turn

_DSN = os.environ.get("LOCAL_AGENT_TEST_PG_DSN")
_NOW = "2026-01-01T00:00:00+00:00"

pytestmark = pytest.mark.skipif(
    not _DSN, reason="set LOCAL_AGENT_TEST_PG_DSN to run Postgres store tests"
)


def _reachable(dsn: str) -> bool:
    try:
        psycopg2.connect(dsn, connect_timeout=3).close()
        return True
    except Exception:
        return False


@pytest.fixture
def store():
    if not _reachable(_DSN):
        pytest.skip("Postgres not reachable at LOCAL_AGENT_TEST_PG_DSN")
    from src.local_agent.memory.pg_storage import PostgresSessionStore

    s = PostgresSessionStore(_DSN)
    created: list[str] = []

    def make(session_id: str):
        created.append(session_id)
        return session_id

    yield s, make
    # Cleanup: remove any rows this test created.
    with psycopg2.connect(_DSN) as conn, conn.cursor() as cur:
        for sid in created:
            cur.execute("DELETE FROM turns WHERE session_id = %s", (sid,))
            cur.execute("DELETE FROM sessions WHERE session_id = %s", (sid,))


def test_pg_roundtrip(store) -> None:
    s, make = store
    sid = make("pytest-roundtrip")
    s.append_turn(sid, Turn("user", "hello"), now=_NOW)
    s.append_turn(sid, Turn("agent", "hi"), now=_NOW)
    turns = s.load_turns(sid)
    assert [(t.role, t.content) for t in turns] == [("user", "hello"), ("agent", "hi")]


def test_pg_limit(store) -> None:
    s, make = store
    sid = make("pytest-limit")
    for i in range(5):
        s.append_turn(sid, Turn("user", f"q{i}"), now=_NOW)
    assert [t.content for t in s.load_turns(sid, limit=2)] == ["q3", "q4"]


def test_pg_unknown_session_empty(store) -> None:
    s, _ = store
    assert s.load_turns("pytest-nonexistent-xyz") == []
