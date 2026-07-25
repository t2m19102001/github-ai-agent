"""Tests for list_files, git_reader, and code_query tools."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.local_agent.tools.code_query import CodeQueryTool
from src.local_agent.tools.git_reader import GitReaderTool
from src.local_agent.tools.list_files import ListFilesTool


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text(
        "class Widget:\n    def spin(self):\n        return 1\n",
        encoding="utf-8",
    )
    (tmp_path / "readme.txt").write_text("hi\n", encoding="utf-8")
    (tmp_path / ".hidden").write_text("secret\n", encoding="utf-8")
    return tmp_path


# --- ListFilesTool ----------------------------------------------------------

def test_list_files_root(repo: Path) -> None:
    result = ListFilesTool(repo).run({"path": ""})
    assert result.ok
    assert "pkg/" in result.content
    assert "readme.txt" in result.content
    assert ".hidden" not in result.content  # dotfiles skipped


def test_list_files_subdir(repo: Path) -> None:
    result = ListFilesTool(repo).run({"path": "pkg"})
    assert result.ok
    assert "mod.py" in result.content


def test_list_files_not_a_dir(repo: Path) -> None:
    result = ListFilesTool(repo).run({"path": "readme.txt"})
    assert not result.ok
    assert "not a directory" in result.content


def test_list_files_blocks_traversal(repo: Path) -> None:
    result = ListFilesTool(repo).run({"path": "../.."})
    assert not result.ok
    assert "escapes repository root" in result.content


# --- CodeQueryTool ----------------------------------------------------------

def test_code_query_finds_class(repo: Path) -> None:
    result = CodeQueryTool(repo).run({"name": "Widget"})
    assert result.ok
    assert "pkg/mod.py:1" in result.content
    assert "class Widget" in result.content


def test_code_query_finds_method(repo: Path) -> None:
    result = CodeQueryTool(repo).run({"name": "spin"})
    assert result.ok
    assert "def spin" in result.content


def test_code_query_missing_symbol(repo: Path) -> None:
    result = CodeQueryTool(repo).run({"name": "DoesNotExist"})
    assert not result.ok
    assert "no definition found" in result.content


def test_code_query_requires_name(repo: Path) -> None:
    assert not CodeQueryTool(repo).run({}).ok


# --- GitReaderTool ----------------------------------------------------------

def _init_git_repo(root: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    git("init")
    git("config", "user.email", "t@t.io")
    git("config", "user.name", "Test")
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    git("add", "a.py")
    git("commit", "-m", "add a.py")


def test_git_reader_log(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    result = GitReaderTool(tmp_path).run({"action": "log"})
    assert result.ok
    assert "add a.py" in result.content


def test_git_reader_rejects_bad_action(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    result = GitReaderTool(tmp_path).run({"action": "push"})
    assert not result.ok
    assert "action must be one of" in result.content


def test_git_reader_blocks_traversal(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    result = GitReaderTool(tmp_path).run({"action": "log", "path": "../../etc"})
    assert not result.ok
    assert "escapes repository root" in result.content
