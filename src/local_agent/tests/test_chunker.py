"""Unit tests for the local agent semantic chunker."""

from __future__ import annotations

from pathlib import Path

from src.local_agent.ingestion.chunker import ChunkLevel, SemanticChunker, chunk_file, chunk_files
from src.local_agent.ingestion.parser import parse_file
from src.local_agent.ingestion.symbols import extract_symbols


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _get_chunk(chunks: list, level: ChunkLevel, qualified_name: str | None = None):
    for item in chunks:
        if item.level != level:
            continue
        if qualified_name is not None and item.qualified_name != qualified_name:
            continue
        return item
    raise AssertionError(f"Chunk not found: level={level}, qualified_name={qualified_name}")


def test_create_file_level_chunk(tmp_path: Path) -> None:
    source = (
        '"""Module docs."""\n\n'
        "import os\n\n"
        "def alpha():\n"
        "    return 1\n"
    )
    target = tmp_path / "module.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    symbols = extract_symbols(parsed)
    chunks = chunk_file(parsed, symbols=symbols)

    file_chunk = _get_chunk(chunks, ChunkLevel.FILE)
    assert file_chunk.file_path == str(target.resolve())
    assert file_chunk.relative_path == "module.py"
    assert file_chunk.docstring == "Module docs."
    assert "import os" in file_chunk.imports
    assert "alpha" in file_chunk.symbols


def test_create_class_level_chunk(tmp_path: Path) -> None:
    source = (
        "class Service:\n"
        "    def run(self):\n"
        "        return 1\n"
    )
    target = tmp_path / "service.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    chunks = chunk_file(parsed)

    class_chunk = _get_chunk(chunks, ChunkLevel.CLASS, "Service")
    assert class_chunk.name == "Service"
    assert class_chunk.start_line == 1
    assert class_chunk.end_line == 3
    assert class_chunk.parent_name == "service.py"
    assert class_chunk.metadata["method_names"] == ["run"]


def test_create_function_level_chunk(tmp_path: Path) -> None:
    source = (
        "def top_level():\n"
        "    return 1\n"
    )
    target = tmp_path / "functions.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    chunks = chunk_file(parsed)

    function_chunk = _get_chunk(chunks, ChunkLevel.FUNCTION, "top_level")
    assert function_chunk.name == "top_level"
    assert function_chunk.start_line == 1
    assert function_chunk.end_line == 2
    assert function_chunk.parent_name == "functions.py"


def test_create_method_level_chunk(tmp_path: Path) -> None:
    source = (
        "class Service:\n"
        "    def run(self):\n"
        "        return 1\n"
    )
    target = tmp_path / "methods.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    chunks = chunk_file(parsed)

    method_chunk = _get_chunk(chunks, ChunkLevel.METHOD, "Service.run")
    assert method_chunk.name == "run"
    assert method_chunk.start_line == 2
    assert method_chunk.end_line == 3
    assert method_chunk.parent_name == "Service"


def test_preserve_line_spans(tmp_path: Path) -> None:
    source = (
        '"""docs"""\n'
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
    chunks = chunk_file(parsed)

    function_chunk = _get_chunk(chunks, ChunkLevel.FUNCTION, "top")
    class_chunk = _get_chunk(chunks, ChunkLevel.CLASS, "A")
    method_chunk = _get_chunk(chunks, ChunkLevel.METHOD, "A.m")

    assert function_chunk.start_line == 3
    assert function_chunk.end_line == 4
    assert class_chunk.start_line == 6
    assert class_chunk.end_line == 8
    assert method_chunk.start_line == 7
    assert method_chunk.end_line == 8


def test_include_imports_docstrings_symbols(tmp_path: Path) -> None:
    source = (
        '"""Module docs."""\n'
        "import os\n"
        "from pkg import helper\n"
        "\n"
        "def top():\n"
        "    return 1\n"
        "\n"
        "class Service:\n"
        "    def run(self):\n"
        "        return 2\n"
    )
    target = tmp_path / "metadata.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    symbols = extract_symbols(parsed)

    object.__setattr__(symbols.functions[0], "docstring", "Top docs.")
    object.__setattr__(symbols.classes[0], "docstring", "Service docs.")
    object.__setattr__(symbols.methods[0], "docstring", "Run docs.")

    chunks = chunk_file(parsed, symbols=symbols)

    file_chunk = _get_chunk(chunks, ChunkLevel.FILE)
    function_chunk = _get_chunk(chunks, ChunkLevel.FUNCTION, "top")
    class_chunk = _get_chunk(chunks, ChunkLevel.CLASS, "Service")
    method_chunk = _get_chunk(chunks, ChunkLevel.METHOD, "Service.run")

    assert "import os" in file_chunk.imports
    assert "from pkg import helper" in file_chunk.imports
    assert file_chunk.symbols == symbols.public_symbols
    assert function_chunk.docstring == "Top docs."
    assert class_chunk.docstring == "Service docs."
    assert method_chunk.docstring == "Run docs."


def test_handle_empty_module(tmp_path: Path) -> None:
    target = tmp_path / "empty.py"
    _write_file(target, "")

    parsed = parse_file(target, repo_root=tmp_path)
    chunks = SemanticChunker().chunk_file(parsed)

    assert len(chunks) == 1
    assert chunks[0].level == ChunkLevel.FILE
    assert chunks[0].metadata["parse_success"] is True
    assert chunks[0].imports == []
    assert chunks[0].symbols == []


def test_handle_parse_error_file_gracefully(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    _write_file(target, "def broken(:\n    return 1\n")

    parsed = parse_file(target, repo_root=tmp_path)
    chunks = chunk_file(parsed)

    assert parsed.parse_success is False
    assert len(chunks) == 1
    assert chunks[0].level == ChunkLevel.FILE
    assert chunks[0].metadata["parse_success"] is False
    assert chunks[0].metadata["parse_errors"]


def test_deterministic_output(tmp_path: Path) -> None:
    first = tmp_path / "b.py"
    second = tmp_path / "a.py"
    _write_file(first, "def b():\n    return 2\n")
    _write_file(second, "def a():\n    return 1\n")

    parsed_first = parse_file(first, repo_root=tmp_path)
    parsed_second = parse_file(second, repo_root=tmp_path)

    chunks_one = chunk_files([parsed_first, parsed_second])
    chunks_two = chunk_files([parsed_second, parsed_first])

    assert chunks_one == chunks_two
    assert [item.relative_path for item in chunks_one if item.level == ChunkLevel.FILE] == [
        "a.py",
        "b.py",
    ]


def test_no_duplicate_chunk_explosion_on_same_file(tmp_path: Path) -> None:
    source = (
        "def top():\n"
        "    return 1\n\n"
        "class Service:\n"
        "    def run(self):\n"
        "        return 2\n"
    )
    target = tmp_path / "single.py"
    _write_file(target, source)

    parsed = parse_file(target, repo_root=tmp_path)
    chunks = chunk_file(parsed)

    ids = [item.id for item in chunks]
    assert len(ids) == len(set(ids))
    assert len(chunks) == 4
