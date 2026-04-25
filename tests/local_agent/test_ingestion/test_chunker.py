"""P0-04 Semantic Chunker tests."""

from __future__ import annotations

from pathlib import Path

from src.local_agent.ingestion.chunker import ChunkLevel, chunk_file, chunk_files
from src.local_agent.ingestion.parser import parse_file, parse_files
from src.local_agent.ingestion.symbols import extract_symbols, extract_symbols_batch


def test_produces_all_four_levels(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    levels = {c.level for c in chunks}
    assert ChunkLevel.FILE in levels
    assert ChunkLevel.CLASS in levels
    assert ChunkLevel.FUNCTION in levels
    assert ChunkLevel.METHOD in levels


def test_exactly_one_file_chunk(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    file_chunks = [c for c in chunks if c.level == ChunkLevel.FILE]
    assert len(file_chunks) == 1


def test_function_and_method_chunk_counts(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    fn_chunks = [c for c in chunks if c.level == ChunkLevel.FUNCTION]
    mth_chunks = [c for c in chunks if c.level == ChunkLevel.METHOD]
    # 3 top-level functions: top_level, async_fn, _private_fn
    assert len(fn_chunks) == 3
    # 2 methods on Greeter: greet, _internal
    assert len(mth_chunks) == 2


def test_docstrings_propagate_to_chunks(sample_file: Path) -> None:
    """Critical: ensure docstring fix flows all the way to chunks."""
    pf = parse_file(sample_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    by_name = {(c.level, c.name): c for c in chunks}
    assert by_name[(ChunkLevel.CLASS, "Greeter")].docstring == "Greeter class docstring."
    assert by_name[(ChunkLevel.FUNCTION, "top_level")].docstring == "Top-level function docstring."
    assert by_name[(ChunkLevel.METHOD, "greet")].docstring == "Greet method docstring."


def test_line_spans_preserved(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    for c in chunks:
        assert c.start_line >= 1
        assert c.end_line >= c.start_line


def test_method_parent_name_is_class(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    for c in chunks:
        if c.level == ChunkLevel.METHOD:
            assert c.parent_name == "Greeter"


def test_chunk_ids_are_unique(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids)), "duplicate chunk ids"


def test_chunk_content_includes_essentials(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    file_chunk = next(c for c in chunks if c.level == ChunkLevel.FILE)
    assert "Module docstring" in file_chunk.content
    assert "Public symbols" in file_chunk.content


def test_failed_parse_yields_only_file_chunk(syntax_error_file: Path) -> None:
    pf = parse_file(syntax_error_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    assert len(chunks) == 1
    assert chunks[0].level == ChunkLevel.FILE
    assert chunks[0].metadata["parse_success"] is False


def test_empty_file_yields_only_file_chunk(empty_file: Path) -> None:
    pf = parse_file(empty_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    assert len(chunks) == 1
    assert chunks[0].level == ChunkLevel.FILE


def test_chunks_deterministic(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    a = chunk_file(pf, extract_symbols(pf))
    b = chunk_file(pf, extract_symbols(pf))
    assert [c.id for c in a] == [c.id for c in b]


def test_chunk_files_batch_deterministic(repo_root: Path) -> None:
    parsed = parse_files(list(repo_root.rglob("*.py")))
    symbols_map = {s.file_path: s for s in extract_symbols_batch(parsed)}
    a = chunk_files(parsed, symbols_map)
    b = chunk_files(list(reversed(parsed)), symbols_map)
    assert [c.id for c in a] == [c.id for c in b]
