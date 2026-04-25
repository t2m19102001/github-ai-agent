"""Unit tests for the local agent Python parser."""

from __future__ import annotations

from pathlib import Path

from src.local_agent.ingestion import PythonParser
from src.local_agent.ingestion.crawler import FileCrawler
from src.local_agent.ingestion.parser import parse_file, parse_files


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parse_module_docstring(tmp_path: Path) -> None:
    target = tmp_path / "pkg" / "module.py"
    _write_file(
        target,
        '"""Module level docs."""\n\nVALUE = 1\n',
    )

    parsed = parse_file(target, repo_root=tmp_path)

    assert parsed.parse_success is True
    assert parsed.relative_path == "pkg/module.py"
    assert parsed.module_docstring == "Module level docs."


def test_parse_import_statements(tmp_path: Path) -> None:
    source = (
        "import os\n"
        "import sys as system\n"
        "from pathlib import Path, PurePosixPath as PP\n"
        "from .subpkg import mod as local_mod\n"
    )
    target = tmp_path / "imports.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)

    assert parsed.parse_success is True
    assert parsed.relative_path == "imports.py"
    assert [(item.kind, item.module, item.names, item.level) for item in parsed.imports] == [
        ("import", None, ["os"], 0),
        ("import", None, ["sys as system"], 0),
        ("from", "pathlib", ["Path", "PurePosixPath as PP"], 0),
        ("from", "subpkg", ["mod as local_mod"], 1),
    ]


def test_parse_top_level_functions(tmp_path: Path) -> None:
    source = (
        "def alpha():\n"
        "    return 1\n\n"
        "async def beta():\n"
        "    return 2\n\n"
        "class C:\n"
        "    def alpha(self):\n"
        "        return 3\n"
    )
    target = tmp_path / "functions.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)

    assert [item.name for item in parsed.functions] == ["alpha", "beta"]
    assert [item.is_async for item in parsed.functions] == [False, True]


def test_parse_classes_and_methods(tmp_path: Path) -> None:
    source = (
        "class Base:\n"
        "    pass\n\n"
        "class Service(Base):\n"
        "    def sync_run(self):\n"
        "        return 1\n\n"
        "    async def async_run(self):\n"
        "        return 2\n"
    )
    target = tmp_path / "classes.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)

    assert [item.name for item in parsed.classes] == ["Base", "Service"]
    assert parsed.classes[1].bases == ["Base"]
    assert [item.name for item in parsed.classes[1].methods] == ["sync_run", "async_run"]
    assert [item.qualified_name for item in parsed.methods] == [
        "Service.sync_run",
        "Service.async_run",
    ]


def test_preserve_line_spans(tmp_path: Path) -> None:
    source = (
        '"""module docs"""\n'
        "\n"
        "import os\n"
        "\n"
        "def top():\n"
        "    return 1\n"
        "\n"
        "class A:\n"
        "    def method(self):\n"
        "        return 2\n"
    )
    target = tmp_path / "lines.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)

    assert parsed.imports[0].line_start == 3
    assert parsed.imports[0].line_end == 3
    assert parsed.functions[0].line_start == 5
    assert parsed.functions[0].line_end == 6
    assert parsed.classes[0].line_start == 8
    assert parsed.classes[0].line_end == 10
    assert parsed.methods[0].line_start == 9
    assert parsed.methods[0].line_end == 10


def test_batch_parse_handles_syntax_errors_gracefully(tmp_path: Path) -> None:
    _write_file(tmp_path / "ok.py", "def ok():\n    return 1\n")
    _write_file(tmp_path / "bad.py", "def broken(:\n    return 1\n")

    parser = PythonParser()
    parsed_files = parser.parse_files(
        [tmp_path / "bad.py", tmp_path / "ok.py"],
        repo_root=tmp_path,
    )

    parsed_by_name = {item.relative_path: item for item in parsed_files}

    assert set(parsed_by_name.keys()) == {"bad.py", "ok.py"}
    assert parsed_by_name["ok.py"].parse_success is True
    assert parsed_by_name["bad.py"].parse_success is False
    assert parsed_by_name["bad.py"].parse_errors
    assert parsed_by_name["bad.py"].parse_errors[0].error_type == "SyntaxError"


def test_output_is_deterministic_across_runs(tmp_path: Path) -> None:
    _write_file(tmp_path / "b.py", "def b():\n    return 2\n")
    _write_file(tmp_path / "a.py", "def a():\n    return 1\n")

    input_paths = [tmp_path / "b.py", tmp_path / "a.py"]

    first = parse_files(input_paths, repo_root=tmp_path)
    second = parse_files(input_paths, repo_root=tmp_path)

    assert first == second
    assert [item.relative_path for item in first] == ["a.py", "b.py"]


def test_parser_works_with_crawler_paths(tmp_path: Path) -> None:
    _write_file(tmp_path / "src" / "one.py", "def one():\n    return 1\n")
    _write_file(tmp_path / "src" / "two.py", "class Two:\n    pass\n")
    _write_file(tmp_path / "README.md", "not python")

    crawl_result = FileCrawler().crawl(tmp_path)
    crawl_paths = [entry["path"] for entry in crawl_result["files"]]

    parsed = parse_files(crawl_paths, repo_root=tmp_path)

    assert [item.relative_path for item in parsed] == ["src/one.py", "src/two.py"]
    assert all(item.parse_success for item in parsed)
