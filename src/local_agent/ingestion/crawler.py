"""
File Crawler Module.

Purpose: Discover and crawl source files respecting .gitignore.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
import os
from pathlib import Path, PurePosixPath
import time
from typing import Any, Iterable, Sequence


DEFAULT_IGNORED_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
        ".idea",
        ".vscode",
    }
)


@dataclass(frozen=True)
class FileRecord:
    """Metadata for one crawled source file."""

    path: str
    relative_path: str
    size_bytes: int
    language: str
    last_modified: str


@dataclass(frozen=True)
class CrawlStats:
    """Summary statistics for one crawl operation."""

    total_files: int
    total_size_bytes: int
    scan_duration_ms: int


@dataclass(frozen=True)
class CrawlResult:
    """Crawler output container."""

    files: list[FileRecord]
    stats: CrawlStats

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": [asdict(record) for record in self.files],
            "stats": asdict(self.stats),
        }


@dataclass(frozen=True)
class _GitIgnoreRule:
    """One parsed gitignore rule."""

    pattern: str
    negated: bool
    directory_only: bool
    anchored: bool

    def matches(self, relative_path: str, is_dir: bool) -> bool:
        normalized = relative_path.strip("/")
        if not normalized:
            return False

        if self.directory_only:
            return self._matches_directory(normalized)
        return self._matches_path(normalized)

    def _matches_directory(self, normalized_path: str) -> bool:
        if self.anchored:
            return normalized_path == self.pattern or normalized_path.startswith(f"{self.pattern}/")

        if "/" in self.pattern:
            if normalized_path == self.pattern or normalized_path.startswith(f"{self.pattern}/"):
                return True
            return _match_pattern(normalized_path, f"**/{self.pattern}")

        return self.pattern in normalized_path.split("/")

    def _matches_path(self, normalized_path: str) -> bool:
        path_name = PurePosixPath(normalized_path).name

        if self.anchored:
            return _match_pattern(normalized_path, self.pattern)

        if "/" in self.pattern:
            return _match_pattern(normalized_path, self.pattern) or _match_pattern(
                normalized_path, f"**/{self.pattern}"
            )

        return _match_pattern(path_name, self.pattern) or _match_pattern(normalized_path, self.pattern)


class _GitIgnoreMatcher:
    """Minimal .gitignore matcher with support for common rules."""

    def __init__(self, rules: Sequence[_GitIgnoreRule]):
        self._rules = tuple(rules)

    @classmethod
    def from_repo_root(cls, repo_root: Path) -> _GitIgnoreMatcher | None:
        gitignore_path = repo_root / ".gitignore"
        if not gitignore_path.exists() or not gitignore_path.is_file():
            return None

        rules: list[_GitIgnoreRule] = []
        try:
            raw_lines = gitignore_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None

        for raw_line in raw_lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            negated = line.startswith("!")
            if negated:
                line = line[1:].strip()
            if not line:
                continue

            anchored = line.startswith("/")
            if anchored:
                line = line.lstrip("/")

            directory_only = line.endswith("/")
            if directory_only:
                line = line.rstrip("/")

            pattern = _normalize_pattern(line)
            if not pattern:
                continue

            rules.append(
                _GitIgnoreRule(
                    pattern=pattern,
                    negated=negated,
                    directory_only=directory_only,
                    anchored=anchored,
                )
            )

        return cls(rules)

    def is_ignored(self, relative_path: str, is_dir: bool) -> bool:
        ignored = False
        for rule in self._rules:
            if rule.matches(relative_path=relative_path, is_dir=is_dir):
                ignored = not rule.negated
        return ignored


class FileCrawler:
    """Crawls files from a repository."""

    def __init__(
        self,
        default_include_patterns: Sequence[str] | None = None,
        default_exclude_patterns: Sequence[str] | None = None,
    ):
        self.default_include_patterns = tuple(default_include_patterns or ())
        self.default_exclude_patterns = tuple(default_exclude_patterns or ())

    def crawl(
        self,
        repo_root: Path | str,
        include_patterns: Sequence[str] | None = None,
        exclude_patterns: Sequence[str] | None = None,
        respect_gitignore: bool = True,
    ) -> dict[str, Any]:
        """
        Crawl Python files from repository.

        Args:
            repo_root: Path to the repository root
            include_patterns: Optional include glob patterns
            exclude_patterns: Optional exclude glob patterns
            respect_gitignore: Whether to apply .gitignore filtering

        Returns:
            Crawl result with file metadata and stats
        """
        repo_root_path = Path(repo_root).expanduser().resolve()
        if not repo_root_path.exists() or not repo_root_path.is_dir():
            raise ValueError(f"Invalid repository root: {repo_root}")

        includes = _normalize_patterns(include_patterns or self.default_include_patterns)
        excludes = _normalize_patterns(exclude_patterns or self.default_exclude_patterns)
        gitignore_matcher = (
            _GitIgnoreMatcher.from_repo_root(repo_root_path) if respect_gitignore else None
        )

        records: list[FileRecord] = []
        start = time.perf_counter()

        skipped_errors = 0

        def _on_walk_error(_: OSError) -> None:
            nonlocal skipped_errors
            skipped_errors += 1

        for current_root, directory_names, file_names in os.walk(
            repo_root_path,
            topdown=True,
            followlinks=False,
            onerror=_on_walk_error,
        ):
            current_root_path = Path(current_root)

            pruned_directories: list[str] = []
            for directory_name in sorted(directory_names):
                if directory_name in DEFAULT_IGNORED_DIRECTORIES:
                    continue

                directory_path = current_root_path / directory_name

                try:
                    if directory_path.is_symlink():
                        continue
                except OSError:
                    skipped_errors += 1
                    continue

                try:
                    relative_directory = directory_path.relative_to(repo_root_path).as_posix()
                except ValueError:
                    continue

                if _matches_patterns(relative_directory, excludes):
                    continue

                if gitignore_matcher and gitignore_matcher.is_ignored(relative_directory, is_dir=True):
                    continue

                pruned_directories.append(directory_name)

            directory_names[:] = pruned_directories

            for file_name in sorted(file_names):
                if not file_name.endswith(".py"):
                    continue

                file_path = current_root_path / file_name

                try:
                    if file_path.is_symlink():
                        continue
                except OSError:
                    skipped_errors += 1
                    continue

                try:
                    relative_file = file_path.relative_to(repo_root_path).as_posix()
                except ValueError:
                    continue

                if includes and not _matches_patterns(relative_file, includes):
                    continue

                if _matches_patterns(relative_file, excludes):
                    continue

                if gitignore_matcher and gitignore_matcher.is_ignored(relative_file, is_dir=False):
                    continue

                try:
                    stat_result = file_path.stat()
                except (FileNotFoundError, PermissionError, OSError):
                    skipped_errors += 1
                    continue

                records.append(
                    FileRecord(
                        path=str(file_path.resolve()),
                        relative_path=relative_file,
                        size_bytes=int(stat_result.st_size),
                        language="python",
                        last_modified=_to_utc_iso8601(stat_result.st_mtime),
                    )
                )

        records.sort(key=lambda record: record.relative_path)

        total_size_bytes = sum(record.size_bytes for record in records)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        result = CrawlResult(
            files=records,
            stats=CrawlStats(
                total_files=len(records),
                total_size_bytes=total_size_bytes,
                scan_duration_ms=elapsed_ms,
            ),
        )

        # Keep this local for easy debugging in case callers need to inspect it.
        _ = skipped_errors

        return result.to_dict()


def crawl_python_files(
    repo_root: Path | str,
    include_patterns: Sequence[str] | None = None,
    exclude_patterns: Sequence[str] | None = None,
    respect_gitignore: bool = True,
) -> dict[str, Any]:
    """Functional API wrapper for crawling Python files."""
    crawler = FileCrawler()
    return crawler.crawl(
        repo_root=repo_root,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        respect_gitignore=respect_gitignore,
    )


def _normalize_patterns(patterns: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for pattern in patterns:
        clean = _normalize_pattern(pattern)
        if clean:
            normalized.append(clean)
    return tuple(normalized)


def _normalize_pattern(pattern: str) -> str:
    clean = pattern.strip().replace("\\", "/")
    while clean.startswith("./"):
        clean = clean[2:]
    return clean


def _matches_patterns(relative_path: str, patterns: Sequence[str]) -> bool:
    if not patterns:
        return False

    path_name = PurePosixPath(relative_path).name
    for pattern in patterns:
        if _match_pattern(relative_path, pattern):
            return True

        if "/" not in pattern and _match_pattern(path_name, pattern):
            return True

    return False


def _match_pattern(value: str, pattern: str) -> bool:
    return PurePosixPath(value).match(pattern) or fnmatch(value, pattern)


def _to_utc_iso8601(timestamp: float) -> str:
    return (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
