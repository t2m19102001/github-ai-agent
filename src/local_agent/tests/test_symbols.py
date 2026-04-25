"""Unit tests for the local agent symbol extractor."""

from __future__ import annotations

from pathlib import Path

from src.local_agent.ingestion.parser import parse_file
from src.local_agent.ingestion.symbols import (
    SymbolExtractor,
    extract_symbols,
    extract_symbols_batch,
)


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_extract_top_level_functions(tmp_path: Path) -> None:
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
    table = extract_symbols(parsed)

    assert [item.name for item in table.functions] == ["alpha", "beta"]
    assert [item.qualified_name for item in table.functions] == ["alpha", "beta"]


def test_extract_classes(tmp_path: Path) -> None:
    source = (
        "class Base:\n"
        "    pass\n\n"
        "class Child(Base):\n"
        "    pass\n"
    )
    target = tmp_path / "classes.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    table = extract_symbols(parsed)

    assert [item.name for item in table.classes] == ["Base", "Child"]
    assert [item.qualified_name for item in table.classes] == ["Base", "Child"]


def test_extract_methods_with_parent_class_relation(tmp_path: Path) -> None:
    source = (
        "class Service:\n"
        "    def run(self):\n"
        "        return 1\n\n"
        "    async def schedule(self):\n"
        "        return 2\n"
    )
    target = tmp_path / "service.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    table = SymbolExtractor().extract(parsed)

    assert [item.qualified_name for item in table.methods] == [
        "Service.run",
        "Service.schedule",
    ]
    assert [item.class_name for item in table.methods] == ["Service", "Service"]
    assert [item.qualified_name for item in table.classes[0].methods] == [
        "Service.run",
        "Service.schedule",
    ]


def test_normalize_imports_correctly(tmp_path: Path) -> None:
    source = (
        "import os\n"
        "import sys as system\n"
        "from pkg.sub import tool as t, helper\n"
        "from .local import value\n"
        "from .. import thing as alias_thing\n"
    )
    target = tmp_path / "imports.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    table = extract_symbols(parsed)

    assert [
        (item.module, item.name, item.alias, item.is_from_import, item.start_line, item.end_line)
        for item in table.imports
    ] == [
        (None, "os", None, False, 1, 1),
        (None, "sys", "system", False, 2, 2),
        ("pkg.sub", "tool", "t", True, 3, 3),
        ("pkg.sub", "helper", None, True, 3, 3),
        (".local", "value", None, True, 4, 4),
        ("..", "thing", "alias_thing", True, 5, 5),
    ]


def test_preserve_line_spans(tmp_path: Path) -> None:
    source = (
        '"""doc"""\n'
        "\n"
        "import os\n"
        "\n"
        "def top():\n"
        "    return 1\n"
        "\n"
        "class A:\n"
        "    def m(self):\n"
        "        return 2\n"
    )
    target = tmp_path / "lines.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    table = extract_symbols(parsed)

    assert table.imports[0].start_line == 3
    assert table.imports[0].end_line == 3
    assert table.functions[0].start_line == 5
    assert table.functions[0].end_line == 6
    assert table.classes[0].start_line == 8
    assert table.classes[0].end_line == 10
    assert table.methods[0].start_line == 9
    assert table.methods[0].end_line == 10


def test_extract_docstrings(tmp_path: Path) -> None:
    source = (
        "def top():\n"
        "    \"\"\"Top level docs.\"\"\"\n"
        "    return 1\n\n"
        "class Service:\n"
        "    \"\"\"Service docs.\"\"\"\n"
        "    def run(self):\n"
        "        \"\"\"Run docs.\"\"\"\n"
        "        return 2\n"
    )
    target = tmp_path / "docstrings.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)

    object.__setattr__(parsed.functions[0], "docstring", "Top level docs.")
    object.__setattr__(parsed.classes[0], "docstring", "Service docs.")
    object.__setattr__(parsed.methods[0], "docstring", "Run docs.")

    table = extract_symbols(parsed)

    assert table.functions[0].docstring == "Top level docs."
    assert table.classes[0].docstring == "Service docs."
    assert table.classes[0].methods[0].docstring == "Run docs."


def test_compute_public_symbols_for_simple_names(tmp_path: Path) -> None:
    source = (
        "def public_fn():\n"
        "    return 1\n\n"
        "def _private_fn():\n"
        "    return 2\n\n"
        "class Service:\n"
        "    def run(self):\n"
        "        return 3\n\n"
        "    def _hidden(self):\n"
        "        return 4\n\n"
        "class _Internal:\n"
        "    def leak(self):\n"
        "        return 5\n"
    )
    target = tmp_path / "publics.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    table = extract_symbols(parsed)

    assert table.public_symbols == ["public_fn", "Service", "Service.run"]


def test_handle_empty_module(tmp_path: Path) -> None:
    target = tmp_path / "empty.py"
    _write_file(target, "")

    parsed = parse_file(target, repo_root=tmp_path)
    table = extract_symbols(parsed)

    assert table.parse_success is True
    assert table.imports == []
    assert table.classes == []
    assert table.functions == []
    assert table.methods == []
    assert table.public_symbols == []


def test_handle_parse_error_input_gracefully(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    _write_file(target, "def broken(:\n    return 1\n")

    parsed = parse_file(target, repo_root=tmp_path)
    table = extract_symbols(parsed)

    assert parsed.parse_success is False
    assert table.parse_success is False
    assert table.parse_errors
    assert table.imports == []
    assert table.classes == []
    assert table.functions == []
    assert table.methods == []
    assert table.public_symbols == []


def test_deterministic_batch_output(tmp_path: Path) -> None:
    first_path = tmp_path / "b.py"
    second_path = tmp_path / "a.py"
    _write_file(first_path, "def b():\n    return 2\n")
    _write_file(second_path, "def a():\n    return 1\n")

    first_parsed = parse_file(first_path, repo_root=tmp_path)
    second_parsed = parse_file(second_path, repo_root=tmp_path)

    batch_one = extract_symbols_batch([first_parsed, second_parsed])
    batch_two = extract_symbols_batch([second_parsed, first_parsed])

    assert [item.relative_path for item in batch_one] == ["a.py", "b.py"]
    assert batch_one == batch_two
