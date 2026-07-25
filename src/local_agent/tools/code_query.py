"""
code_query tool — find where a function or class is defined.

Retrieval finds *semantically* similar chunks; this tool answers the exact
structural question "where is ``LocalAgent`` defined?" by scanning Python files
for ``def <name>`` / ``class <name>`` lines. Deterministic and read-only.

It complements read_file: the agent locates a symbol here, then reads the file.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.local_agent.tools.base import ToolResult

_MAX_HITS = 30
# Skip heavy/irrelevant trees so a query stays fast and on-signal.
_SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "data"}


class CodeQueryTool:
    """Grep Python files for the definition of a symbol (function or class)."""

    name = "code_query"
    description = "Find where a Python function or class is defined by name."
    args_schema = {"name": "exact symbol name, e.g. LocalAgent or query"}

    def __init__(self, repo_root: Path | str) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()

    def run(self, args: dict) -> ToolResult:
        name = args.get("name")
        if not name or not isinstance(name, str):
            return ToolResult.failure("code_query needs a string 'name' argument")

        # Match `def name(` or `class name(` / `class name:` at a def boundary.
        pattern = re.compile(
            rf"^\s*(?:def|class)\s+{re.escape(name)}\b"
        )
        hits: list[str] = []
        for py_file in self._iter_python_files():
            try:
                lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for lineno, line in enumerate(lines, start=1):
                if pattern.match(line):
                    rel = py_file.relative_to(self.repo_root).as_posix()
                    hits.append(f"{rel}:{lineno}: {line.strip()}")
                    if len(hits) >= _MAX_HITS:
                        break
            if len(hits) >= _MAX_HITS:
                break

        if not hits:
            return ToolResult.failure(f"no definition found for {name!r}")
        return ToolResult.success("\n".join(hits))

    def _iter_python_files(self):
        for path in self.repo_root.rglob("*.py"):
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            yield path


__all__ = ["CodeQueryTool"]
