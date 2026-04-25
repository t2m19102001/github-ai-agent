"""P0-03 Symbol Extractor tests."""

from __future__ import annotations

from pathlib import Path

from src.local_agent.ingestion.parser import parse_file, parse_files
from src.local_agent.ingestion.symbols import extract_symbols, extract_symbols_batch


def test_extract_basic_symbols(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    st = extract_symbols(pf)
    assert st.parse_success
    fn_names = {f.name for f in st.functions}
    assert {"top_level", "async_fn", "_private_fn"} <= fn_names
    assert {c.name for c in st.classes} == {"Greeter"}


def test_docstrings_preserved_through_extractor(sample_file: Path) -> None:
    """Regression: docstrings must flow parser → symbol table."""
    pf = parse_file(sample_file)
    st = extract_symbols(pf)
    fn_doc = {f.name: f.docstring for f in st.functions}
    assert fn_doc["top_level"] == "Top-level function docstring."
    assert fn_doc["async_fn"] == "Async function docstring."

    cls = st.classes[0]
    assert cls.docstring == "Greeter class docstring."

    method_doc = {m.name: m.docstring for m in cls.methods}
    assert method_doc["greet"] == "Greet method docstring."


def test_public_symbols_excludes_underscored(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    st = extract_symbols(pf)
    assert "top_level" in st.public_symbols
    assert "async_fn" in st.public_symbols
    assert "Greeter" in st.public_symbols
    assert "_private_fn" not in st.public_symbols
    # Private methods of a public class are also excluded
    assert "Greeter._internal" not in st.public_symbols


def test_method_class_name_correct(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    st = extract_symbols(pf)
    for method in st.methods:
        assert method.class_name == "Greeter"
        assert method.qualified_name == f"Greeter.{method.name}"


def test_parse_failure_propagates(syntax_error_file: Path) -> None:
    pf = parse_file(syntax_error_file)
    st = extract_symbols(pf)
    assert st.parse_success is False
    assert st.parse_errors
    assert "SyntaxError" in st.parse_errors[0]
    assert st.functions == []
    assert st.classes == []


def test_extract_batch_is_deterministic(repo_root: Path) -> None:
    parsed = parse_files(list(repo_root.rglob("*.py")))
    a = extract_symbols_batch(parsed)
    b = extract_symbols_batch(list(reversed(parsed)))
    assert [s.file_path for s in a] == [s.file_path for s in b]


def test_imports_normalized(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    st = extract_symbols(pf)
    # `from typing import List, Optional as Opt` → 2 ImportSymbol entries
    typing_imports = [i for i in st.imports if i.module == "typing"]
    assert len(typing_imports) == 2
    aliased = next(i for i in typing_imports if i.alias == "Opt")
    assert aliased.name == "Optional"
    assert aliased.is_from_import is True
