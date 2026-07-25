"""
list_files tool — let the LLM see what files exist in a directory.

Retrieval and read_file both assume the model already knows a path. This tool
answers the prior question "what is in here?", so the agent can discover files
before reading them. Read-only and confined to the repo root.
"""

from __future__ import annotations

from pathlib import Path

from src.local_agent.tools.base import ToolResult, is_within

# Cap entries so a huge directory cannot flood the context window.
_MAX_ENTRIES = 200


class ListFilesTool:
    """List entries of a directory inside the repo root (non-recursive)."""

    name = "list_files"
    description = "List files and folders in a repository directory."
    args_schema = {"path": "repo-relative directory, '' or '.' for the root"}

    def __init__(self, repo_root: Path | str) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()

    def run(self, args: dict) -> ToolResult:
        raw_path = args.get("path", "")
        if not isinstance(raw_path, str):
            return ToolResult.failure("list_files 'path' must be a string")

        target = (self.repo_root / raw_path).resolve()
        if not is_within(self.repo_root, target):
            return ToolResult.failure(f"path escapes repository root: {raw_path!r}")
        if not target.is_dir():
            return ToolResult.failure(f"not a directory: {raw_path!r}")

        entries = []
        for child in sorted(target.iterdir()):
            if child.name.startswith("."):
                continue  # skip dotfiles/dotdirs for a cleaner listing
            suffix = "/" if child.is_dir() else ""
            entries.append(child.name + suffix)

        if not entries:
            return ToolResult.success("(empty directory)")
        truncated = entries[:_MAX_ENTRIES]
        text = "\n".join(truncated)
        if len(entries) > _MAX_ENTRIES:
            text += f"\n... ({len(entries) - _MAX_ENTRIES} more)"
        return ToolResult.success(text)


__all__ = ["ListFilesTool"]
