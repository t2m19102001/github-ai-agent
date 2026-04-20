#!/usr/bin/env python3
"""Guard test to prevent unresolved git merge markers from landing in commits."""

from pathlib import Path


CONFLICT_MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "node_modules"}
SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf"}


def _iter_text_files(repo_root: Path):
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_EXTENSIONS:
            continue
        yield path


def test_repository_has_no_unresolved_merge_markers():
    repo_root = Path(__file__).resolve().parent.parent
    conflicts = []

    for path in _iter_text_files(repo_root):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Skip binary or non-UTF8 files.
            continue

        lines = content.splitlines()
        for lineno, line in enumerate(lines, start=1):
            if line.startswith(CONFLICT_MARKERS):
                conflicts.append(f"{path.relative_to(repo_root)}:{lineno}: {line[:20]}")

    assert not conflicts, "Found unresolved merge conflict markers:\n" + "\n".join(conflicts)
