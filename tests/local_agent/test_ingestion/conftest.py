"""Shared fixtures for ingestion tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


SAMPLE_WITH_DOCSTRINGS = textwrap.dedent(
    '''
    """Module-level docstring."""

    import os
    from typing import List, Optional as Opt

    CONSTANT = 42

    def top_level(arg):
        """Top-level function docstring."""
        return arg


    async def async_fn():
        """Async function docstring."""
        return None


    def _private_fn():
        """Private function (single-underscore)."""
        return None


    class Greeter:
        """Greeter class docstring."""

        @staticmethod
        def greet(name: str) -> str:
            """Greet method docstring."""
            return f"Hello {name}"

        def _internal(self):
            """Private method."""
            return None
    '''
).lstrip()


SAMPLE_NO_DOCSTRINGS = textwrap.dedent(
    """
    def foo():
        return 1

    class Bar:
        def baz(self):
            return 2
    """
).lstrip()


SAMPLE_SYNTAX_ERROR = "def broken(:\n    return\n"


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """A throw-away repo root with a few python files and a .gitignore."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "module_a.py").write_text(SAMPLE_WITH_DOCSTRINGS)
    (tmp_path / "pkg" / "module_b.py").write_text(SAMPLE_NO_DOCSTRINGS)

    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "secret.py").write_text("X = 1\n")

    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "generated.py").write_text("Y = 2\n")

    (tmp_path / ".gitignore").write_text("ignored/\n")
    return tmp_path


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """A single sample file with full docstring coverage."""
    target = tmp_path / "sample.py"
    target.write_text(SAMPLE_WITH_DOCSTRINGS)
    return target


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    target = tmp_path / "empty.py"
    target.write_text("")
    return target


@pytest.fixture
def syntax_error_file(tmp_path: Path) -> Path:
    target = tmp_path / "broken.py"
    target.write_text(SAMPLE_SYNTAX_ERROR)
    return target
