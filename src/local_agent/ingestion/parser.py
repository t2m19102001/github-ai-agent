"""
Python Parser Module.

Purpose: Parse Python files using Python stdlib AST.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParseErrorInfo:
    """Error details for one file parse failure."""

    error_type: str
    message: str
    line: int | None
    column: int | None


@dataclass(frozen=True)
class ImportInfo:
    """One import statement."""

    kind: str
    module: str | None
    names: list[str]
    level: int
    line_start: int
    line_end: int


@dataclass(frozen=True)
class FunctionInfo:
    """One top-level function."""

    name: str
    is_async: bool
    decorators: list[str]
    line_start: int
    line_end: int
    docstring: str | None = None


@dataclass(frozen=True)
class MethodInfo:
    """One class method."""

    class_name: str
    name: str
    qualified_name: str
    is_async: bool
    decorators: list[str]
    line_start: int
    line_end: int
    docstring: str | None = None


@dataclass(frozen=True)
class ClassInfo:
    """One top-level class and its methods."""

    name: str
    bases: list[str]
    methods: list[MethodInfo]
    line_start: int
    line_end: int
    docstring: str | None = None


@dataclass(frozen=True)
class ParsedFile:
    """Parsed output for one Python file."""

    path: str
    relative_path: str | None
    module_docstring: str | None
    imports: list[ImportInfo]
    classes: list[ClassInfo]
    functions: list[FunctionInfo]
    methods: list[MethodInfo]
    parse_success: bool
    parse_errors: list[ParseErrorInfo]

    def to_dict(self) -> dict[str, object]:
        """Serialize parsed output to a dictionary."""
        return asdict(self)


class PythonParser:
    """Parses Python files into structured metadata for ingestion."""

    def parse(
        self,
        file_path: Path | str,
        repo_root: Path | str | None = None,
    ) -> ParsedFile:
        """Compatibility wrapper for parse_file."""
        return self.parse_file(path=file_path, repo_root=repo_root)

    def parse_file(
        self,
        path: Path | str,
        repo_root: Path | str | None = None,
    ) -> ParsedFile:
        """Parse one Python file and return structured metadata."""
        file_path = Path(path).expanduser().resolve()
        relative_path = _relative_path(file_path=file_path, repo_root=repo_root)

        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            return _build_error_result(
                file_path=file_path,
                relative_path=relative_path,
                error_type=type(error).__name__,
                message=str(error),
                line=None,
                column=None,
            )

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as error:
            return _build_error_result(
                file_path=file_path,
                relative_path=relative_path,
                error_type="SyntaxError",
                message=error.msg,
                line=error.lineno,
                column=error.offset,
            )

        imports: list[ImportInfo] = []
        classes: list[ClassInfo] = []
        functions: list[FunctionInfo] = []
        methods: list[MethodInfo] = []

        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.append(_build_import_info(node))
                continue

            if isinstance(node, ast.ImportFrom):
                imports.append(_build_from_import_info(node))
                continue

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(_build_function_info(node))
                continue

            if isinstance(node, ast.ClassDef):
                class_info = _build_class_info(node)
                classes.append(class_info)
                methods.extend(class_info.methods)

        return ParsedFile(
            path=str(file_path),
            relative_path=relative_path,
            module_docstring=ast.get_docstring(tree, clean=False),
            imports=imports,
            classes=classes,
            functions=functions,
            methods=methods,
            parse_success=True,
            parse_errors=[],
        )

    def parse_files(
        self,
        paths: list[Path | str],
        repo_root: Path | str | None = None,
    ) -> list[ParsedFile]:
        """Parse multiple files deterministically, without failing on one bad file."""
        sorted_paths = sorted(
            (Path(item).expanduser().resolve() for item in paths),
            key=lambda item: item.as_posix(),
        )
        return [self.parse_file(path=item, repo_root=repo_root) for item in sorted_paths]


def parse_file(
    path: Path | str,
    repo_root: Path | str | None = None,
) -> ParsedFile:
    """Functional API for parsing one Python file."""
    return PythonParser().parse_file(path=path, repo_root=repo_root)


def parse_files(
    paths: list[Path | str],
    repo_root: Path | str | None = None,
) -> list[ParsedFile]:
    """Functional API for parsing multiple Python files."""
    return PythonParser().parse_files(paths=paths, repo_root=repo_root)


def _build_error_result(
    file_path: Path,
    relative_path: str | None,
    error_type: str,
    message: str,
    line: int | None,
    column: int | None,
) -> ParsedFile:
    return ParsedFile(
        path=str(file_path),
        relative_path=relative_path,
        module_docstring=None,
        imports=[],
        classes=[],
        functions=[],
        methods=[],
        parse_success=False,
        parse_errors=[
            ParseErrorInfo(
                error_type=error_type,
                message=message,
                line=line,
                column=column,
            )
        ],
    )


def _relative_path(file_path: Path, repo_root: Path | str | None) -> str | None:
    if repo_root is None:
        return None

    root = Path(repo_root).expanduser().resolve()
    try:
        return file_path.relative_to(root).as_posix()
    except ValueError:
        return None


def _node_span(node: ast.AST) -> tuple[int, int]:
    start = int(getattr(node, "lineno", 0))
    end = int(getattr(node, "end_lineno", start))
    return start, end


def _alias_to_text(alias: ast.alias) -> str:
    if alias.asname:
        return f"{alias.name} as {alias.asname}"
    return alias.name


def _expr_to_text(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def _build_import_info(node: ast.Import) -> ImportInfo:
    start, end = _node_span(node)
    return ImportInfo(
        kind="import",
        module=None,
        names=[_alias_to_text(alias) for alias in node.names],
        level=0,
        line_start=start,
        line_end=end,
    )


def _build_from_import_info(node: ast.ImportFrom) -> ImportInfo:
    start, end = _node_span(node)
    return ImportInfo(
        kind="from",
        module=node.module,
        names=[_alias_to_text(alias) for alias in node.names],
        level=int(node.level),
        line_start=start,
        line_end=end,
    )


def _build_function_info(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
    start, end = _node_span(node)
    return FunctionInfo(
        name=node.name,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        decorators=[_expr_to_text(item) for item in node.decorator_list],
        line_start=start,
        line_end=end,
        docstring=ast.get_docstring(node, clean=False),
    )


def _build_method_info(
    class_name: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> MethodInfo:
    start, end = _node_span(node)
    return MethodInfo(
        class_name=class_name,
        name=node.name,
        qualified_name=f"{class_name}.{node.name}",
        is_async=isinstance(node, ast.AsyncFunctionDef),
        decorators=[_expr_to_text(item) for item in node.decorator_list],
        line_start=start,
        line_end=end,
        docstring=ast.get_docstring(node, clean=False),
    )


def _build_class_info(node: ast.ClassDef) -> ClassInfo:
    start, end = _node_span(node)

    methods: list[MethodInfo] = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_build_method_info(class_name=node.name, node=child))

    return ClassInfo(
        name=node.name,
        bases=[_expr_to_text(base) for base in node.bases],
        methods=methods,
        line_start=start,
        line_end=end,
        docstring=ast.get_docstring(node, clean=False),
    )


__all__ = [
    "ParseErrorInfo",
    "ImportInfo",
    "FunctionInfo",
    "MethodInfo",
    "ClassInfo",
    "ParsedFile",
    "PythonParser",
    "parse_file",
    "parse_files",
]
