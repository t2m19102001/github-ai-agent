"""
Local AI Agent CLI.

Two subcommands:

    index <repo_path>    Crawl + parse + chunk + embed + write FAISS index.
    query "question"     Run the RAG pipeline against an existing index.

Usage:
    python -m src.local_agent.cli index .
    python -m src.local_agent.cli query "What does AuthService.login do?"
    python -m src.local_agent.cli query --json "..."
    python -m src.local_agent.cli --version
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence

from src.local_agent.core import AgentResponse, LocalAgent, QueryConfig


VERSION = "0.1.0"
DEFAULT_INDEX_DIR = os.environ.get(
    "LOCAL_AGENT_INDEX_PATH", "data/local_agent/indices/code"
)
DEFAULT_MODEL = os.environ.get("LOCAL_AGENT_MODEL", "llama3:8b")

AgentFactory = Callable[..., LocalAgent]
IndexPipeline = Callable[..., dict]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-agent",
        description="Local AI agent for codebase Q&A (read-only, suggest-only).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"local-agent {VERSION}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # ---- index ----
    index_p = subparsers.add_parser(
        "index",
        help="Build a FAISS index for a repository.",
        description="Crawl Python files, parse, chunk, embed, and persist a FAISS index.",
    )
    index_p.add_argument(
        "repo_path",
        type=str,
        help="Path to the repository root to index.",
    )
    index_p.add_argument(
        "--index-dir",
        type=str,
        default=DEFAULT_INDEX_DIR,
        help=f"Output directory for the FAISS index (default: {DEFAULT_INDEX_DIR}).",
    )
    index_p.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Embedding model name (default: {DEFAULT_MODEL}).",
    )
    index_p.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size (default: 32).",
    )
    index_p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print extra progress info.",
    )

    # ---- query ----
    query_p = subparsers.add_parser(
        "query",
        help="Ask a question against the indexed codebase.",
        description="Retrieve relevant chunks, build a context window, call the local LLM.",
    )
    query_p.add_argument(
        "question",
        type=str,
        help="Natural-language question about the codebase.",
    )
    query_p.add_argument("-k", "--top-k", type=int, default=8)
    query_p.add_argument("--max-context-tokens", type=int, default=32000)
    query_p.add_argument("--model", type=str, default=DEFAULT_MODEL)
    query_p.add_argument("--index-dir", type=str, default=DEFAULT_INDEX_DIR)
    query_p.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit the response as JSON.",
    )
    query_p.add_argument("-v", "--verbose", action="store_true")

    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    agent_factory: AgentFactory | None = None,
    index_pipeline: IndexPipeline | None = None,
    stdout=None,
    stderr=None,
) -> int:
    """CLI entry point. Returns process exit code."""
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "index":
        return _cmd_index(args, out=out, err=err, pipeline=index_pipeline)
    if args.command == "query":
        return _cmd_query(args, out=out, err=err, agent_factory=agent_factory)

    err.write(f"Error: unknown command {args.command!r}\n")
    return 1


# ---------------------------------------------------------------------------
# Subcommand: index
# ---------------------------------------------------------------------------


def _cmd_index(args, *, out, err, pipeline: IndexPipeline | None) -> int:
    repo_path = Path(args.repo_path).expanduser().resolve()
    if not repo_path.is_dir():
        err.write(f"Error: repo_path is not a directory: {repo_path}\n")
        return 2

    runner = pipeline or _run_index_pipeline
    try:
        stats = runner(
            repo_path=repo_path,
            index_dir=Path(args.index_dir).expanduser().resolve(),
            model_name=args.model,
            batch_size=args.batch_size,
            verbose=args.verbose,
            log=out,
        )
    except Exception as error:
        err.write(f"Error: indexing failed: {error}\n")
        if _debug_enabled(args.verbose):
            import traceback

            traceback.print_exc(file=err)
        return 1

    out.write(
        f"Indexed {stats['total_chunks']} chunks "
        f"from {stats['total_files']} files "
        f"in {stats['elapsed_ms']} ms.\n"
        f"Index written to: {stats['index_dir']}\n"
    )
    return 0


def _run_index_pipeline(
    *,
    repo_path: Path,
    index_dir: Path,
    model_name: str,
    batch_size: int,
    verbose: bool,
    log,
) -> dict:
    """Default ingestion pipeline: crawl → parse → symbols → chunk → embed → index."""
    from src.local_agent.indexing.index_builder import IndexBuilder
    from src.local_agent.ingestion import (
        chunk_files,
        crawl_python_files,
        embed_chunks,
        extract_symbols_batch,
        parse_files,
    )

    started = time.perf_counter()

    if verbose:
        log.write(f"Crawling Python files under {repo_path}...\n")
    crawl = crawl_python_files(repo_path)
    paths = [Path(record["path"]) for record in crawl["files"]]
    if verbose:
        log.write(f"  found {len(paths)} files\n")

    if not paths:
        raise RuntimeError(f"no Python files found under {repo_path}")

    if verbose:
        log.write("Parsing AST...\n")
    parsed = parse_files(paths, repo_root=repo_path)

    if verbose:
        log.write("Extracting symbols...\n")
    symbols = extract_symbols_batch(parsed)
    symbols_map = {s.file_path: s for s in symbols}

    if verbose:
        log.write("Chunking...\n")
    chunks = chunk_files(parsed, symbols_map)
    if verbose:
        log.write(f"  produced {len(chunks)} chunks\n")

    if verbose:
        log.write(f"Embedding with {model_name} (batch_size={batch_size})...\n")
    embedded = embed_chunks(chunks, model_name=model_name, batch_size=batch_size)

    if verbose:
        log.write(f"Writing FAISS index to {index_dir}...\n")
    result = IndexBuilder(index_dir).build(embedded)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "total_files": len(paths),
        "total_chunks": result.total_chunks,
        "elapsed_ms": elapsed_ms,
        "index_dir": str(index_dir),
    }


# ---------------------------------------------------------------------------
# Subcommand: query
# ---------------------------------------------------------------------------


def _cmd_query(args, *, out, err, agent_factory: AgentFactory | None) -> int:
    config = QueryConfig(
        top_k=args.top_k,
        max_context_tokens=args.max_context_tokens,
    )
    factory = agent_factory or _build_default_agent

    try:
        agent = factory(
            config=config,
            index_dir=args.index_dir,
            model_name=args.model,
        )
    except Exception as error:
        err.write(f"Error: failed to initialize agent: {error}\n")
        if _debug_enabled(args.verbose):
            import traceback

            traceback.print_exc(file=err)
        return 1

    try:
        response = agent.query(args.question)
    except ValueError as error:
        err.write(f"Error: {error}\n")
        return 2
    except Exception as error:
        err.write(f"Error: query failed: {error}\n")
        if _debug_enabled(args.verbose):
            import traceback

            traceback.print_exc(file=err)
        return 1

    if args.as_json:
        out.write(_format_json(response) + "\n")
    else:
        out.write(_format_human(response, verbose=args.verbose) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _format_human(response: AgentResponse, *, verbose: bool) -> str:
    lines: list[str] = [
        "Question:",
        f"  {response.question}",
        "",
        "Answer:",
        *(f"  {line}" for line in response.answer.splitlines() or [""]),
        "",
        f"Confidence: {response.confidence:.2f}",
        f"Model: {response.model_name}",
        f"Latency: {response.latency_ms} ms",
    ]

    if verbose:
        lines.extend(
            [
                "",
                "Context:",
                f"  Retrieved chunks: {response.total_retrieved} "
                f"(used in context: {len(response.retrieved_chunks)})",
                f"  Context tokens: {response.total_context_tokens}",
            ]
        )
        if response.retrieved_chunks:
            lines.append("  Chunks:")
            lines.extend(f"    - {cid}" for cid in response.retrieved_chunks)
        if response.warnings:
            lines.append("  Warnings:")
            lines.extend(f"    - {w}" for w in response.warnings)
    elif response.warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in response.warnings)

    return "\n".join(lines)


def _format_json(response: AgentResponse) -> str:
    return json.dumps(dataclasses.asdict(response), indent=2, default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _debug_enabled(verbose_flag: bool) -> bool:
    return verbose_flag or os.environ.get("LOCAL_AGENT_DEBUG") == "1"


# ---------------------------------------------------------------------------
# Production wiring (lazy)
# ---------------------------------------------------------------------------


def _build_default_agent(
    *,
    config: QueryConfig,
    index_dir: str,
    model_name: str,
) -> LocalAgent:
    from src.local_agent.retrieval.context_builder import ContextBuilder
    from src.local_agent.retrieval.retriever import BasicRetriever

    retriever = BasicRetriever(index_dir=index_dir, model_name=model_name)
    context_builder = ContextBuilder(
        max_tokens=config.max_context_tokens,
        reserve_tokens=config.reserve_tokens,
    )
    llm_client = _OllamaAdapter(model_name=model_name)
    return LocalAgent(
        retriever=retriever,
        context_builder=context_builder,
        llm_client=llm_client,
        config=config,
    )


class _OllamaAdapter:
    """Translate LLMClientProtocol(generate) → OllamaProvider(call(messages))."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._provider = None

    def _get_provider(self):
        if self._provider is None:
            from src.llm.ollama import OllamaProvider

            self._provider = OllamaProvider(model=self.model_name)
        return self._provider

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1200,
        temperature: float = 0.0,
    ) -> str:
        provider = self._get_provider()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = provider.call(messages, temperature=temperature, max_tokens=max_tokens)
        if result is None:
            raise RuntimeError("Ollama returned no response (connection or timeout error)")
        return result


if __name__ == "__main__":
    sys.exit(main())
