"""
read_file tool — hand the LLM the full text of a repository file.

Retrieval only surfaces *chunks*; sometimes the model needs the whole file to
answer well. This tool provides that, but stays strictly inside the repository
root and read-only.

Security: the requested path is resolved and checked to be **inside** the
repo root, so ``../../etc/passwd`` or an absolute path outside the repo is
rejected. This is the single most important guard in a read-only agent.
"""

from __future__ import annotations

from pathlib import Path

from src.local_agent.tools.base import ToolResult, is_within

# Cap the returned text so a huge file cannot blow the LLM context window.
_MAX_CHARS = 20_000


class FileReaderTool:
    """Read a UTF-8 text file that lives under the repo root."""

    name = "read_file"
    description = "Read the full text of a file inside the repository."
    args_schema = {"path": "repo-relative path to the file, e.g. src/foo.py"}

    def __init__(self, repo_root: Path | str) -> None:
        # Resolve once so every request is compared against a canonical root.
        self.repo_root = Path(repo_root).expanduser().resolve()

    def run(self, args: dict) -> ToolResult:
        raw_path = args.get("path")
        if not raw_path or not isinstance(raw_path, str):
            return ToolResult.failure("read_file needs a string 'path' argument")

        # Resolve the target and confirm it stays within the repo root.
        target = (self.repo_root / raw_path).resolve()
        if not is_within(self.repo_root, target):
            return ToolResult.failure(
                f"path escapes repository root: {raw_path!r}"
            )
        if not target.is_file():
            return ToolResult.failure(f"file not found: {raw_path!r}")

        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            return ToolResult.failure(f"could not read {raw_path!r}: {error}")

        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + "\n... (truncated)"
        return ToolResult.success(text)


__all__ = ["FileReaderTool"]
