"""
Symbol Extractor Module.

Purpose: Extract normalized symbol tables from parsed Python files.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.local_agent.ingestion.parser import ParsedFile, ParseErrorInfo


@dataclass(frozen=True)
class ImportSymbol:
    """Normalized import symbol."""

    module: str | None
    name: str
    alias: str | None
    is_from_import: bool
    start_line: int
    end_line: int


@dataclass(frozen=True)
class FunctionSymbol:
    """Top-level function symbol."""

    name: str
    qualified_name: str
    docstring: str | None
    start_line: int
    end_line: int
    decorators: list[str]


@dataclass(frozen=True)
class MethodSymbol:
    """Method symbol belonging to a class."""

    name: str
    qualified_name: str
    class_name: str
    docstring: str | None
    start_line: int
    end_line: int
    decorators: list[str]


@dataclass(frozen=True)
class ClassSymbol:
    """Class symbol and its methods."""

    name: str
    qualified_name: str
    docstring: str | None
    start_line: int
    end_line: int
    methods: list[MethodSymbol]


@dataclass(frozen=True)
class SymbolTable:
    """Symbol table extracted from one parsed file."""

    file_path: str
    relative_path: str | None
    module_docstring: str | None
    imports: list[ImportSymbol]
    classes: list[ClassSymbol]
    functions: list[FunctionSymbol]
    methods: list[MethodSymbol]
    public_symbols: list[str]
    parse_success: bool
    parse_errors: list[str]


class SymbolExtractor:
    """Extracts normalized symbols from parser output."""

    def extract(self, parsed_file: ParsedFile) -> SymbolTable:
        """Extract symbols from a single parsed file."""
        if not parsed_file.parse_success:
            return SymbolTable(
                file_path=parsed_file.path,
                relative_path=parsed_file.relative_path,
                module_docstring=parsed_file.module_docstring,
                imports=[],
                classes=[],
                functions=[],
                methods=[],
                public_symbols=[],
                parse_success=False,
                parse_errors=[_format_parse_error(item) for item in parsed_file.parse_errors],
            )

        imports: list[ImportSymbol] = []
        for import_info in parsed_file.imports:
            module_name = _normalize_import_module(import_info.module, import_info.level)
            for raw_name in import_info.names:
                name, alias = _split_alias(raw_name)
                imports.append(
                    ImportSymbol(
                        module=module_name,
                        name=name,
                        alias=alias,
                        is_from_import=(import_info.kind == "from"),
                        start_line=import_info.line_start,
                        end_line=import_info.line_end,
                    )
                )

        functions: list[FunctionSymbol] = [
            FunctionSymbol(
                name=item.name,
                qualified_name=item.name,
                docstring=getattr(item, "docstring", None),
                start_line=item.line_start,
                end_line=item.line_end,
                decorators=list(item.decorators),
            )
            for item in parsed_file.functions
        ]

        methods: list[MethodSymbol] = [
            MethodSymbol(
                name=item.name,
                qualified_name=item.qualified_name,
                class_name=item.class_name,
                docstring=getattr(item, "docstring", None),
                start_line=item.line_start,
                end_line=item.line_end,
                decorators=list(item.decorators),
            )
            for item in parsed_file.methods
        ]

        methods_by_class: dict[str, list[MethodSymbol]] = {}
        for method in methods:
            methods_by_class.setdefault(method.class_name, []).append(method)

        classes: list[ClassSymbol] = [
            ClassSymbol(
                name=item.name,
                qualified_name=item.name,
                docstring=getattr(item, "docstring", None),
                start_line=item.line_start,
                end_line=item.line_end,
                methods=methods_by_class.get(item.name, []),
            )
            for item in parsed_file.classes
        ]

        public_symbols = _compute_public_symbols(functions=functions, classes=classes)

        return SymbolTable(
            file_path=parsed_file.path,
            relative_path=parsed_file.relative_path,
            module_docstring=parsed_file.module_docstring,
            imports=imports,
            classes=classes,
            functions=functions,
            methods=methods,
            public_symbols=public_symbols,
            parse_success=True,
            parse_errors=[],
        )

    def extract_batch(self, parsed_files: list[ParsedFile]) -> list[SymbolTable]:
        """Extract symbols from multiple parsed files deterministically."""
        ordered_files = sorted(parsed_files, key=_parsed_file_sort_key)
        return [self.extract(item) for item in ordered_files]


def extract_symbols(parsed_file: ParsedFile) -> SymbolTable:
    """Functional API for extracting symbols from one parsed file."""
    return SymbolExtractor().extract(parsed_file)


def extract_symbols_batch(parsed_files: list[ParsedFile]) -> list[SymbolTable]:
    """Functional API for extracting symbols from many parsed files."""
    return SymbolExtractor().extract_batch(parsed_files)


def _split_alias(raw_name: str) -> tuple[str, str | None]:
    if " as " not in raw_name:
        return raw_name, None

    name, alias = raw_name.split(" as ", maxsplit=1)
    return name.strip(), alias.strip()


def _normalize_import_module(module: str | None, level: int) -> str | None:
    if level <= 0:
        return module

    prefix = "." * level
    if module:
        return f"{prefix}{module}"
    return prefix


def _compute_public_symbols(
    functions: list[FunctionSymbol],
    classes: list[ClassSymbol],
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add_if_public(symbol_name: str) -> None:
        if symbol_name.startswith("_"):
            return
        if symbol_name in seen:
            return
        seen.add(symbol_name)
        ordered.append(symbol_name)

    for function_symbol in functions:
        add_if_public(function_symbol.name)

    for class_symbol in classes:
        add_if_public(class_symbol.name)
        for method_symbol in class_symbol.methods:
            if class_symbol.name.startswith("_"):
                continue
            if method_symbol.name.startswith("_"):
                continue
            add_if_public(method_symbol.qualified_name)

    return ordered


def _format_parse_error(error: ParseErrorInfo) -> str:
    location_parts: list[str] = []
    if error.line is not None:
        location_parts.append(f"line={error.line}")
    if error.column is not None:
        location_parts.append(f"column={error.column}")

    location = f" ({', '.join(location_parts)})" if location_parts else ""
    return f"{error.error_type}: {error.message}{location}"


def _parsed_file_sort_key(parsed_file: ParsedFile) -> tuple[str, str]:
    relative = parsed_file.relative_path or ""
    return relative, parsed_file.path


__all__ = [
    "ImportSymbol",
    "FunctionSymbol",
    "MethodSymbol",
    "ClassSymbol",
    "SymbolTable",
    "SymbolExtractor",
    "extract_symbols",
    "extract_symbols_batch",
]
