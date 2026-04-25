"""
Ingestion Module.

Purpose: Parse and extract structure from source code.
Input: Source files
Output: Parsed AST, symbol table, semantic chunks, embeddings.

Components:
    crawler:  File discovery (respects .gitignore)
    parser:   Python AST parsing (stdlib ast)
    symbols:  Symbol extraction (classes, functions, imports)
    chunker:  Semantic chunking (4 levels)
    embedder: Sentence-transformer embeddings (lazy load)
"""

from src.local_agent.ingestion.crawler import (
    CrawlResult,
    CrawlStats,
    FileCrawler,
    FileRecord,
    crawl_python_files,
)
from src.local_agent.ingestion.parser import (
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    MethodInfo,
    ParseErrorInfo,
    ParsedFile,
    PythonParser,
    parse_file,
    parse_files,
)
from src.local_agent.ingestion.symbols import (
    ClassSymbol,
    FunctionSymbol,
    ImportSymbol,
    MethodSymbol,
    SymbolExtractor,
    SymbolTable,
    extract_symbols,
    extract_symbols_batch,
)
from src.local_agent.ingestion.chunker import (
    ChunkLevel,
    CodeChunk,
    SemanticChunker,
    chunk_file,
    chunk_files,
)
from src.local_agent.ingestion.embedder import (
    EmbeddedChunk,
    Embedder,
    embed_chunks,
    to_embed_text,
)

__all__ = [
    # crawler
    "FileCrawler",
    "FileRecord",
    "CrawlStats",
    "CrawlResult",
    "crawl_python_files",
    # parser
    "PythonParser",
    "ParsedFile",
    "ParseErrorInfo",
    "ImportInfo",
    "FunctionInfo",
    "MethodInfo",
    "ClassInfo",
    "parse_file",
    "parse_files",
    # symbols
    "SymbolExtractor",
    "SymbolTable",
    "ImportSymbol",
    "FunctionSymbol",
    "MethodSymbol",
    "ClassSymbol",
    "extract_symbols",
    "extract_symbols_batch",
    # chunker
    "SemanticChunker",
    "CodeChunk",
    "ChunkLevel",
    "chunk_file",
    "chunk_files",
    # embedder
    "Embedder",
    "EmbeddedChunk",
    "embed_chunks",
    "to_embed_text",
]
