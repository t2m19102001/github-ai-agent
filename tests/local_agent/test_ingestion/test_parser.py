"""P0-02 Python Parser tests."""

from __future__ import annotations

from pathlib import Path

from src.local_agent.ingestion.parser import parse_file, parse_files


def test_parses_module_docstring(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    assert pf.parse_success
    assert pf.module_docstring == "Module-level docstring."


def test_extracts_per_node_docstrings(sample_file: Path) -> None:
    """Regression test for the docstring contract bug (P0-02 → P0-03)."""
    pf = parse_file(sample_file)
    fn_by_name = {f.name: f for f in pf.functions}
    assert fn_by_name["top_level"].docstring == "Top-level function docstring."
    assert fn_by_name["async_fn"].docstring == "Async function docstring."

    cls = pf.classes[0]
    assert cls.docstring == "Greeter class docstring."

    method_by_name = {m.name: m for m in cls.methods}
    assert method_by_name["greet"].docstring == "Greet method docstring."
    assert method_by_name["_internal"].docstring == "Private method."


def test_extracts_imports(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    kinds = {(imp.kind, imp.module) for imp in pf.imports}
    assert ("import", None) in kinds
    assert ("from", "typing") in kinds


def test_async_function_detected(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    async_fns = [f for f in pf.functions if f.is_async]
    assert len(async_fns) == 1
    assert async_fns[0].name == "async_fn"


def test_method_decorators_captured(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    greet = next(m for m in pf.classes[0].methods if m.name == "greet")
    assert "staticmethod" in greet.decorators


def test_syntax_error_returns_error_result(syntax_error_file: Path) -> None:
    pf = parse_file(syntax_error_file)
    assert pf.parse_success is False
    assert len(pf.parse_errors) == 1
    assert pf.parse_errors[0].error_type == "SyntaxError"


def test_empty_file_parses_successfully(empty_file: Path) -> None:
    pf = parse_file(empty_file)
    assert pf.parse_success
    assert pf.module_docstring is None
    assert pf.functions == []
    assert pf.classes == []


def test_parse_files_is_deterministic(repo_root: Path) -> None:
    paths = list(repo_root.rglob("*.py"))
    a = parse_files(paths)
    b = parse_files(list(reversed(paths)))
    assert [pf.path for pf in a] == [pf.path for pf in b]


def test_relative_path_computed(repo_root: Path) -> None:
    target = repo_root / "pkg" / "module_a.py"
    pf = parse_file(target, repo_root=repo_root)
    assert pf.relative_path == "pkg/module_a.py"


def test_line_spans_preserved(sample_file: Path) -> None:
    pf = parse_file(sample_file)
    for fn in pf.functions:
        assert fn.line_start >= 1
        assert fn.line_end >= fn.line_start
    for cls in pf.classes:
        assert cls.line_end >= cls.line_start
        for m in cls.methods:
            assert m.line_start >= cls.line_start
            assert m.line_end <= cls.line_end
