"""Tests for SQLite session persistence."""

from __future__ import annotations

from pathlib import Path

from src.local_agent.memory.storage import SessionStore, Turn

_NOW = "2026-01-01T00:00:00+00:00"


def test_append_and_load_roundtrip(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "s.db")
    store.ensure_session("sess1", now=_NOW)
    store.append_turn("sess1", Turn("user", "hello"), now=_NOW)
    store.append_turn("sess1", Turn("agent", "hi there"), now=_NOW)

    turns = store.load_turns("sess1")
    assert [(t.role, t.content) for t in turns] == [
        ("user", "hello"),
        ("agent", "hi there"),
    ]


def test_load_unknown_session_is_empty(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "s.db")
    assert store.load_turns("missing") == []


def test_ensure_session_is_idempotent(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "s.db")
    store.ensure_session("s", now=_NOW)
    store.ensure_session("s", now=_NOW)  # must not raise or duplicate
    store.append_turn("s", Turn("user", "x"), now=_NOW)
    assert len(store.load_turns("s")) == 1


def test_load_turns_respects_limit(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "s.db")
    store.ensure_session("s", now=_NOW)
    for i in range(5):
        store.append_turn("s", Turn("user", f"q{i}"), now=_NOW)
    recent = store.load_turns("s", limit=2)
    assert [t.content for t in recent] == ["q3", "q4"]


def test_persists_across_new_store_instance(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    store1 = SessionStore(db)
    store1.ensure_session("s", now=_NOW)
    store1.append_turn("s", Turn("user", "remember me"), now=_NOW)

    # A brand-new store object opening the same file sees the data.
    store2 = SessionStore(db)
    assert store2.load_turns("s")[-1].content == "remember me"


def test_separate_sessions_are_isolated(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "s.db")
    store.append_turn("a", Turn("user", "in-a"), now=_NOW)
    store.append_turn("b", Turn("user", "in-b"), now=_NOW)
    assert [t.content for t in store.load_turns("a")] == ["in-a"]
    assert [t.content for t in store.load_turns("b")] == ["in-b"]
