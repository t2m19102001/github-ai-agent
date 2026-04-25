"""Unit tests for the local agent Python crawler."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from src.local_agent.ingestion.crawler import FileCrawler


def _write_file(path: Path, content: str = "print('ok')\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relative_paths(result: dict) -> list[str]:
    return [entry["relative_path"] for entry in result["files"]]


def test_only_python_files_included(tmp_path: Path) -> None:
    _write_file(tmp_path / "main.py")
    _write_file(tmp_path / "notes.txt", "notes")
    _write_file(tmp_path / "scripts" / "worker.py")
    _write_file(tmp_path / "data.json", "{}")

    result = FileCrawler().crawl(tmp_path)

    assert _relative_paths(result) == ["main.py", "scripts/worker.py"]
    assert result["stats"]["total_files"] == 2


def test_default_ignore_directories_are_skipped(tmp_path: Path) -> None:
    _write_file(tmp_path / "src" / "keep.py")
    _write_file(tmp_path / ".git" / "ignored.py")
    _write_file(tmp_path / "__pycache__" / "ignored.py")
    _write_file(tmp_path / "node_modules" / "ignored.py")
    _write_file(tmp_path / ".venv" / "ignored.py")

    result = FileCrawler().crawl(tmp_path)

    assert _relative_paths(result) == ["src/keep.py"]


def test_include_patterns_respected(tmp_path: Path) -> None:
    _write_file(tmp_path / "src" / "direct.py")
    _write_file(tmp_path / "src" / "nested" / "deep.py")
    _write_file(tmp_path / "scripts" / "tool.py")

    result = FileCrawler().crawl(
        tmp_path,
        include_patterns=["src/*.py", "src/**/*.py"],
    )

    assert _relative_paths(result) == ["src/direct.py", "src/nested/deep.py"]


def test_exclude_patterns_respected(tmp_path: Path) -> None:
    _write_file(tmp_path / "src" / "keep.py")
    _write_file(tmp_path / "src" / "generated" / "skip.py")
    _write_file(tmp_path / "tests" / "skip_test.py")

    result = FileCrawler().crawl(
        tmp_path,
        exclude_patterns=["src/generated/**", "tests/**"],
    )

    assert _relative_paths(result) == ["src/keep.py"]


def test_output_is_stably_sorted_by_relative_path(tmp_path: Path) -> None:
    _write_file(tmp_path / "zeta.py")
    _write_file(tmp_path / "alpha.py")
    _write_file(tmp_path / "middle.py")

    result = FileCrawler().crawl(tmp_path)
    rel_paths = _relative_paths(result)

    assert rel_paths == sorted(rel_paths)


def test_scan_continues_on_file_stat_error(tmp_path: Path, monkeypatch) -> None:
    _write_file(tmp_path / "ok.py")
    _write_file(tmp_path / "bad.py")

    original_stat = Path.stat

    def flaky_stat(self: Path, *args, **kwargs):
        if self.name == "bad.py":
            raise PermissionError("simulated permission error")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", flaky_stat)

    result = FileCrawler().crawl(tmp_path)

    assert _relative_paths(result) == ["ok.py"]
    assert result["stats"]["total_files"] == 1


def test_metadata_fields_are_populated_correctly(tmp_path: Path) -> None:
    content = "print('hello')\n"
    target = tmp_path / "src" / "main.py"
    _write_file(target, content)

    known_timestamp = 1713744000
    os.utime(target, (known_timestamp, known_timestamp))

    result = FileCrawler().crawl(tmp_path)

    record = result["files"][0]
    assert Path(record["path"]).is_absolute()
    assert record["relative_path"] == "src/main.py"
    assert record["size_bytes"] == len(content.encode("utf-8"))
    assert record["language"] == "python"
    assert record["last_modified"].endswith("Z")

    parsed = datetime.fromisoformat(record["last_modified"].replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


def test_gitignore_is_respected_when_enabled(tmp_path: Path) -> None:
    _write_file(tmp_path / ".gitignore", "ignored.py\nignored_dir/\n",)
    _write_file(tmp_path / "ignored.py")
    _write_file(tmp_path / "ignored_dir" / "nested.py")
    _write_file(tmp_path / "kept.py")

    result = FileCrawler().crawl(tmp_path, respect_gitignore=True)

    assert _relative_paths(result) == ["kept.py"]


def test_gitignore_can_be_disabled(tmp_path: Path) -> None:
    _write_file(tmp_path / ".gitignore", "ignored.py\nignored_dir/\n")
    _write_file(tmp_path / "ignored.py")
    _write_file(tmp_path / "ignored_dir" / "nested.py")
    _write_file(tmp_path / "kept.py")

    result = FileCrawler().crawl(tmp_path, respect_gitignore=False)

    assert _relative_paths(result) == ["ignored.py", "ignored_dir/nested.py", "kept.py"]
