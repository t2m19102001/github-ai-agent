"""
git_reader tool — expose read-only git history for a repository file.

Sometimes the answer lives in *how* code changed, not just its current text:
"when was this function last touched?", "what did the recent commits do?".
This tool runs a whitelisted, read-only git command and returns its output.

Safety:
* Only ``log`` and ``diff`` are allowed — never a state-changing git command.
* The optional file path is confined to the repo root (no traversal).
* Output is size-capped and the subprocess is time-bounded.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.local_agent.tools.base import ToolResult, is_within

_MAX_CHARS = 8_000
_TIMEOUT_SECONDS = 15
_ALLOWED = ("log", "diff")


class GitReaderTool:
    """Run a read-only ``git log``/``git diff`` inside the repo root."""

    name = "git_reader"
    description = "Read git history: recent commit log or diff for the repo/a file."
    args_schema = {
        "action": "'log' or 'diff'",
        "path": "optional repo-relative file to scope the command",
    }

    def __init__(self, repo_root: Path | str) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()

    def run(self, args: dict) -> ToolResult:
        action = args.get("action", "log")
        if action not in _ALLOWED:
            return ToolResult.failure(
                f"git_reader action must be one of {_ALLOWED}, got {action!r}"
            )

        cmd = ["git", "-C", str(self.repo_root), action]
        if action == "log":
            cmd += ["--oneline", "-n", "15"]

        raw_path = args.get("path")
        if raw_path:
            if not isinstance(raw_path, str):
                return ToolResult.failure("git_reader 'path' must be a string")
            target = (self.repo_root / raw_path).resolve()
            if not is_within(self.repo_root, target):
                return ToolResult.failure(
                    f"path escapes repository root: {raw_path!r}"
                )
            cmd += ["--", raw_path]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError:
            return ToolResult.failure("git is not installed or not on PATH")
        except subprocess.TimeoutExpired:
            return ToolResult.failure("git command timed out")

        if proc.returncode != 0:
            return ToolResult.failure(
                f"git {action} failed: {proc.stderr.strip() or 'unknown error'}"
            )

        out = proc.stdout.strip() or "(no output)"
        if len(out) > _MAX_CHARS:
            out = out[:_MAX_CHARS] + "\n... (truncated)"
        return ToolResult.success(out)


__all__ = ["GitReaderTool"]
