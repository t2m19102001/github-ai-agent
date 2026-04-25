"""
Semantic Chunker Module.

Purpose: Create hierarchical semantic chunks from parsed files and symbols.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.local_agent.ingestion.parser import ParsedFile
from src.local_agent.ingestion.symbols import SymbolTable, extract_symbols


class ChunkLevel(str, Enum):
    """Chunk hierarchy level."""

    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


@dataclass(frozen=True)
class CodeChunk:
    """One semantic chunk with metadata for downstream indexing."""

    id: str
    level: ChunkLevel
    file_path: str
    relative_path: str | None
    name: str | None
    qualified_name: str | None
    start_line: int
    end_line: int
    content: str
    docstring: str | None
    imports: list[str]
    symbols: list[str]
    parent_name: str | None
    metadata: dict[str, Any]
    token_count: int | None


class SemanticChunker:
    """Creates semantic chunks from parser and symbol outputs."""

    def chunk(self, ast: Any) -> list[CodeChunk]:
        """
        Backward-compatible wrapper that delegates to chunk_file.

        Args:
            ast: Parsed file metadata

        Returns:
            List of semantic chunks
        """
        if not isinstance(ast, ParsedFile):
            raise TypeError("SemanticChunker.chunk expects ParsedFile input")
        return self.chunk_file(ast)

    def chunk_file(
        self,
        parsed_file: ParsedFile,
        symbols: SymbolTable | None = None,
    ) -> list[CodeChunk]:
        """Create semantic chunks for one parsed file."""
        symbol_table = symbols or extract_symbols(parsed_file)
        imports = _collect_import_strings(parsed_file=parsed_file, symbols=symbol_table)
        public_symbols = list(symbol_table.public_symbols)
        file_parent = parsed_file.relative_path or parsed_file.path
        file_start = 1
        file_end = _file_end_line(parsed_file)

        file_content_lines = [
            f"File: {file_parent}",
            f"Parse status: {'success' if parsed_file.parse_success else 'failed'}",
            f"Imports: {', '.join(imports) if imports else '(none)'}",
            f"Public symbols: {', '.join(public_symbols) if public_symbols else '(none)'}",
        ]
        if parsed_file.module_docstring:
            file_content_lines.append(f"Module docstring: {parsed_file.module_docstring}")
        if symbol_table.parse_errors:
            file_content_lines.append(f"Parse errors: {'; '.join(symbol_table.parse_errors)}")

        chunks: list[CodeChunk] = [
            CodeChunk(
                id=_build_chunk_id(
                    level=ChunkLevel.FILE,
                    relative_path=parsed_file.relative_path,
                    file_path=parsed_file.path,
                    qualified_name="module",
                    start_line=file_start,
                    end_line=file_end,
                ),
                level=ChunkLevel.FILE,
                file_path=parsed_file.path,
                relative_path=parsed_file.relative_path,
                name=None,
                qualified_name=None,
                start_line=file_start,
                end_line=file_end,
                content="\n".join(file_content_lines),
                docstring=parsed_file.module_docstring,
                imports=imports,
                symbols=public_symbols,
                parent_name=None,
                metadata={
                    "chunk_type": "file",
                    "parse_success": parsed_file.parse_success,
                    "parse_errors": list(symbol_table.parse_errors),
                },
                token_count=_token_count("\n".join(file_content_lines)),
            )
        ]

        if not parsed_file.parse_success:
            return chunks

        function_docstrings = {
            item.qualified_name: item.docstring
            for item in symbol_table.functions
        }
        class_docstrings = {
            item.qualified_name: item.docstring
            for item in symbol_table.classes
        }
        method_docstrings = {
            item.qualified_name: item.docstring
            for item in symbol_table.methods
        }

        ordered_classes = sorted(
            parsed_file.classes,
            key=lambda item: (item.line_start, item.line_end, item.name),
        )
        for class_info in ordered_classes:
            class_methods = sorted(
                class_info.methods,
                key=lambda item: (item.line_start, item.line_end, item.name),
            )
            method_names = [item.name for item in class_methods]
            class_docstring = getattr(class_info, "docstring", None)
            if class_docstring is None:
                class_docstring = class_docstrings.get(class_info.name)

            class_content_lines = [
                f"Class: {class_info.name}",
                f"Methods: {', '.join(method_names) if method_names else '(none)'}",
            ]
            if class_info.bases:
                class_content_lines.append(f"Bases: {', '.join(class_info.bases)}")
            if class_docstring:
                class_content_lines.append(f"Docstring: {class_docstring}")

            class_symbols = [class_info.name]
            class_symbols.extend(item.qualified_name for item in class_methods)

            chunks.append(
                CodeChunk(
                    id=_build_chunk_id(
                        level=ChunkLevel.CLASS,
                        relative_path=parsed_file.relative_path,
                        file_path=parsed_file.path,
                        qualified_name=class_info.name,
                        start_line=class_info.line_start,
                        end_line=class_info.line_end,
                    ),
                    level=ChunkLevel.CLASS,
                    file_path=parsed_file.path,
                    relative_path=parsed_file.relative_path,
                    name=class_info.name,
                    qualified_name=class_info.name,
                    start_line=class_info.line_start,
                    end_line=class_info.line_end,
                    content="\n".join(class_content_lines),
                    docstring=class_docstring,
                    imports=imports,
                    symbols=class_symbols,
                    parent_name=file_parent,
                    metadata={
                        "chunk_type": "class",
                        "bases": list(class_info.bases),
                        "method_names": method_names,
                    },
                    token_count=_token_count("\n".join(class_content_lines)),
                )
            )

        ordered_functions = sorted(
            parsed_file.functions,
            key=lambda item: (item.line_start, item.line_end, item.name),
        )
        for function_info in ordered_functions:
            function_docstring = getattr(function_info, "docstring", None)
            if function_docstring is None:
                function_docstring = function_docstrings.get(function_info.name)

            function_content_lines = [f"Function: {function_info.name}"]
            if function_docstring:
                function_content_lines.append(f"Docstring: {function_docstring}")

            chunks.append(
                CodeChunk(
                    id=_build_chunk_id(
                        level=ChunkLevel.FUNCTION,
                        relative_path=parsed_file.relative_path,
                        file_path=parsed_file.path,
                        qualified_name=function_info.name,
                        start_line=function_info.line_start,
                        end_line=function_info.line_end,
                    ),
                    level=ChunkLevel.FUNCTION,
                    file_path=parsed_file.path,
                    relative_path=parsed_file.relative_path,
                    name=function_info.name,
                    qualified_name=function_info.name,
                    start_line=function_info.line_start,
                    end_line=function_info.line_end,
                    content="\n".join(function_content_lines),
                    docstring=function_docstring,
                    imports=imports,
                    symbols=[function_info.name],
                    parent_name=file_parent,
                    metadata={
                        "chunk_type": "function",
                        "is_async": function_info.is_async,
                        "decorators": list(function_info.decorators),
                    },
                    token_count=_token_count("\n".join(function_content_lines)),
                )
            )

        ordered_methods = sorted(
            parsed_file.methods,
            key=lambda item: (item.line_start, item.line_end, item.qualified_name),
        )
        for method_info in ordered_methods:
            method_docstring = getattr(method_info, "docstring", None)
            if method_docstring is None:
                method_docstring = method_docstrings.get(method_info.qualified_name)

            method_content_lines = [
                f"Method: {method_info.qualified_name}",
                f"Class: {method_info.class_name}",
            ]
            if method_docstring:
                method_content_lines.append(f"Docstring: {method_docstring}")

            chunks.append(
                CodeChunk(
                    id=_build_chunk_id(
                        level=ChunkLevel.METHOD,
                        relative_path=parsed_file.relative_path,
                        file_path=parsed_file.path,
                        qualified_name=method_info.qualified_name,
                        start_line=method_info.line_start,
                        end_line=method_info.line_end,
                    ),
                    level=ChunkLevel.METHOD,
                    file_path=parsed_file.path,
                    relative_path=parsed_file.relative_path,
                    name=method_info.name,
                    qualified_name=method_info.qualified_name,
                    start_line=method_info.line_start,
                    end_line=method_info.line_end,
                    content="\n".join(method_content_lines),
                    docstring=method_docstring,
                    imports=imports,
                    symbols=[method_info.qualified_name],
                    parent_name=method_info.class_name,
                    metadata={
                        "chunk_type": "method",
                        "class_name": method_info.class_name,
                        "is_async": method_info.is_async,
                        "decorators": list(method_info.decorators),
                    },
                    token_count=_token_count("\n".join(method_content_lines)),
                )
            )

        return _deduplicate_chunks(chunks)

    def chunk_files(
        self,
        parsed_files: list[ParsedFile],
        symbols_map: dict[str, SymbolTable] | None = None,
    ) -> list[CodeChunk]:
        """Create semantic chunks for many parsed files deterministically."""
        ordered_files = sorted(parsed_files, key=lambda item: (item.relative_path or "", item.path))

        chunks: list[CodeChunk] = []
        for parsed_file in ordered_files:
            symbols = _resolve_symbols(parsed_file=parsed_file, symbols_map=symbols_map)
            chunks.extend(self.chunk_file(parsed_file=parsed_file, symbols=symbols))

        return chunks


def chunk_file(
    parsed_file: ParsedFile,
    symbols: SymbolTable | None = None,
) -> list[CodeChunk]:
    """Functional API for chunking one parsed file."""
    return SemanticChunker().chunk_file(parsed_file=parsed_file, symbols=symbols)


def chunk_files(
    parsed_files: list[ParsedFile],
    symbols_map: dict[str, SymbolTable] | None = None,
) -> list[CodeChunk]:
    """Functional API for chunking multiple parsed files."""
    return SemanticChunker().chunk_files(parsed_files=parsed_files, symbols_map=symbols_map)


def _resolve_symbols(
    parsed_file: ParsedFile,
    symbols_map: dict[str, SymbolTable] | None,
) -> SymbolTable | None:
    if symbols_map is None:
        return None

    if parsed_file.relative_path and parsed_file.relative_path in symbols_map:
        return symbols_map[parsed_file.relative_path]

    return symbols_map.get(parsed_file.path)


def _collect_import_strings(parsed_file: ParsedFile, symbols: SymbolTable) -> list[str]:
    if symbols.imports:
        return [
            _format_symbol_import(
                module=item.module,
                name=item.name,
                alias=item.alias,
                is_from_import=item.is_from_import,
            )
            for item in symbols.imports
        ]

    imports: list[str] = []
    for item in parsed_file.imports:
        normalized_module = _normalize_import_module(module=item.module, level=item.level)
        for raw_name in item.names:
            if item.kind == "from":
                imports.append(f"from {normalized_module} import {raw_name}")
            else:
                imports.append(f"import {raw_name}")
    return imports


def _format_symbol_import(
    module: str | None,
    name: str,
    alias: str | None,
    is_from_import: bool,
) -> str:
    if is_from_import:
        statement = f"from {module} import {name}"
    else:
        statement = f"import {name}"

    if alias:
        return f"{statement} as {alias}"
    return statement


def _normalize_import_module(module: str | None, level: int) -> str:
    if level <= 0:
        return module or ""

    prefix = "." * level
    if module:
        return f"{prefix}{module}"
    return prefix


def _build_chunk_id(
    level: ChunkLevel,
    relative_path: str | None,
    file_path: str,
    qualified_name: str,
    start_line: int,
    end_line: int,
) -> str:
    path_key = relative_path or file_path
    return f"{level.value}:{path_key}:{qualified_name}:{start_line}:{end_line}"


def _file_end_line(parsed_file: ParsedFile) -> int:
    try:
        source = Path(parsed_file.path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        source = ""

    if source:
        return max(1, len(source.splitlines()))

    line_candidates: list[int] = [1]
    line_candidates.extend(item.line_end for item in parsed_file.imports)
    line_candidates.extend(item.line_end for item in parsed_file.classes)
    line_candidates.extend(item.line_end for item in parsed_file.functions)
    line_candidates.extend(item.line_end for item in parsed_file.methods)
    return max(line_candidates)


def _token_count(content: str) -> int:
    return len(content.split())


def _deduplicate_chunks(chunks: list[CodeChunk]) -> list[CodeChunk]:
    seen: set[str] = set()
    ordered: list[CodeChunk] = []
    for chunk in chunks:
        if chunk.id in seen:
            continue
        seen.add(chunk.id)
        ordered.append(chunk)
    return ordered


__all__ = [
    "ChunkLevel",
    "CodeChunk",
    "SemanticChunker",
    "chunk_file",
    "chunk_files",
]
