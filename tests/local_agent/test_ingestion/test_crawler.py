"""P0-01 File Crawler tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.local_agent.ingestion.crawler import FileCrawler, crawl_python_files


def test_crawl_finds_python_files(repo_root: Path) -> None:
    result = FileCrawler().crawl(repo_root)
    rel_paths = [f["relative_path"] for f in result["files"]]
    assert "pkg/module_a.py" in rel_paths
    assert "pkg/module_b.py" in rel_paths
    assert "pkg/__init__.py" in rel_paths


def test_crawl_respects_gitignore(repo_root: Path) -> None:
    result = FileCrawler().crawl(repo_root, respect_gitignore=True)
    rel_paths = [f["relative_path"] for f in result["files"]]
    assert not any(p.startswith("ignored/") for p in rel_paths)


def test_crawl_ignores_default_directories(repo_root: Path) -> None:
    result = FileCrawler().crawl(repo_root)
    rel_paths = [f["relative_path"] for f in result["files"]]
    # `build` is in DEFAULT_IGNORED_DIRECTORIES — must be pruned.
    assert not any(p.startswith("build/") for p in rel_paths)


def test_crawl_output_is_deterministic(repo_root: Path) -> None:
    a = FileCrawler().crawl(repo_root)
    b = FileCrawler().crawl(repo_root)
    assert [f["relative_path"] for f in a["files"]] == [f["relative_path"] for f in b["files"]]
    # Sorted by relative_path
    rel_paths = [f["relative_path"] for f in a["files"]]
    assert rel_paths == sorted(rel_paths)


def test_crawl_records_have_required_fields(repo_root: Path) -> None:
    result = FileCrawler().crawl(repo_root)
    assert result["files"], "expected at least one record"
    sample = result["files"][0]
    assert set(sample.keys()) >= {"path", "relative_path", "size_bytes", "language", "last_modified"}
    assert sample["language"] == "python"
    assert sample["size_bytes"] >= 0


def test_crawl_empty_repo(tmp_path: Path) -> None:
    result = FileCrawler().crawl(tmp_path)
    assert result["files"] == []
    assert result["stats"]["total_files"] == 0
    assert result["stats"]["total_size_bytes"] == 0


def test_crawl_invalid_root_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        FileCrawler().crawl(tmp_path / "does-not-exist")


def test_functional_api_matches_class(repo_root: Path) -> None:
    fn_result = crawl_python_files(repo_root)
    cls_result = FileCrawler().crawl(repo_root)
    assert [f["relative_path"] for f in fn_result["files"]] == [
        f["relative_path"] for f in cls_result["files"]
    ]
