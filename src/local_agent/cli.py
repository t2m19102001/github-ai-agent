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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from src.local_agent.core import AgentResponse, LocalAgent, QueryConfig
from src.local_agent.config import LocalAgentConfig


VERSION = "0.1.0"
_CONFIG_OVERRIDE = os.environ.get("LOCAL_AGENT_CONFIG")
_FILE_CONFIG = LocalAgentConfig(_CONFIG_OVERRIDE) if _CONFIG_OVERRIDE else LocalAgentConfig()
DEFAULT_INDEX_DIR = os.environ.get(
    "LOCAL_AGENT_INDEX_PATH",
    str(Path(_FILE_CONFIG.get("paths.indices_dir", "data/local_agent/indices")) / "code"),
)
# Embedding model (sentence-transformers) — used to build/search the FAISS index.
# Must match between `index` and `query`; it is NOT the LLM.
DEFAULT_EMBED_MODEL = os.environ.get(
    "LOCAL_AGENT_EMBED_MODEL",
    _FILE_CONFIG.get("indexing.embedding_model", "all-MiniLM-L6-v2"),
)
# LLM model (Ollama) — the "brain" that writes the answer. Independent of embeddings.
DEFAULT_LLM_MODEL = os.environ.get(
    "LOCAL_AGENT_MODEL", _FILE_CONFIG.get("llm.model", "llama3.2:3b")
)
# Ollama HTTP timeout (seconds). Generous default: slow CPU-only boxes need it.
DEFAULT_LLM_TIMEOUT = int(
    os.environ.get("LOCAL_AGENT_TIMEOUT", _FILE_CONFIG.get("llm.timeout_seconds", 600))
)

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
        "--embed-model",
        dest="embed_model",
        type=str,
        default=DEFAULT_EMBED_MODEL,
        help=(
            "Sentence-transformers embedding model "
            f"(default: {DEFAULT_EMBED_MODEL}). Not the LLM."
        ),
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
    query_p.add_argument(
        "--embed-model",
        dest="embed_model",
        type=str,
        default=DEFAULT_EMBED_MODEL,
        help=(
            "Embedding model for retrieval; must match the one used at index "
            f"time (default: {DEFAULT_EMBED_MODEL})."
        ),
    )
    query_p.add_argument(
        "--model",
        type=str,
        default=DEFAULT_LLM_MODEL,
        help=f"Ollama LLM model that writes the answer (default: {DEFAULT_LLM_MODEL}).",
    )
    query_p.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_LLM_TIMEOUT,
        help=f"Ollama request timeout in seconds (default: {DEFAULT_LLM_TIMEOUT}).",
    )
    query_p.add_argument("--index-dir", type=str, default=DEFAULT_INDEX_DIR)
    query_p.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit the response as JSON.",
    )
    query_p.add_argument("-v", "--verbose", action="store_true")

    # ---- agent (tool-calling loop) ----
    agent_p = subparsers.add_parser(
        "agent",
        help="Answer a question using the tool-calling loop (reads files/git).",
        description=(
            "Drive the LLM through a read-only tool-calling loop: it can list "
            "files, read files, find symbols, and inspect git history."
        ),
    )
    agent_p.add_argument(
        "question",
        type=str,
        help="Natural-language task, e.g. 'read configs/localagent.yaml and ...'",
    )
    agent_p.add_argument(
        "--model",
        type=str,
        default=DEFAULT_LLM_MODEL,
        help=f"Ollama LLM model (default: {DEFAULT_LLM_MODEL}).",
    )
    agent_p.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_LLM_TIMEOUT,
        help=f"Ollama request timeout in seconds (default: {DEFAULT_LLM_TIMEOUT}).",
    )
    agent_p.add_argument(
        "--repo-root",
        type=str,
        default=".",
        help="Repository root the tools operate within (default: current dir).",
    )
    agent_p.add_argument(
        "--max-iters",
        type=int,
        default=4,
        help="Maximum tool-calling turns before stopping (default: 4).",
    )
    agent_p.add_argument(
        "--session",
        type=str,
        default=None,
        help="Session id to remember across runs (enables multi-turn memory).",
    )
    agent_p.add_argument(
        "--session-db",
        type=str,
        default="data/local_agent/sessions.db",
        help="SQLite file storing session history.",
    )
    agent_p.add_argument(
        "--history-turns",
        type=int,
        default=6,
        help="How many recent turns to feed back as context (default: 6).",
    )
    agent_p.add_argument(
        "--index-dir",
        type=str,
        default=None,
        help="FAISS index dir. If given, enables the RAG-backed search_code tool.",
    )
    agent_p.add_argument(
        "--embed-model",
        dest="embed_model",
        type=str,
        default=DEFAULT_EMBED_MODEL,
        help=f"Embedding model for search_code (default: {DEFAULT_EMBED_MODEL}).",
    )
    agent_p.add_argument("-v", "--verbose", action="store_true")

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
    if args.command == "agent":
        return _cmd_agent(args, out=out, err=err)

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
            model_name=args.embed_model,
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
    # Only the default factory understands embed_model/timeout; injected test
    # factories keep the simpler (config, index_dir, model_name) signature.
    extra = (
        {}
        if agent_factory is not None
        else {"embed_model": args.embed_model, "timeout": args.timeout}
    )

    try:
        agent = factory(
            config=config,
            index_dir=args.index_dir,
            model_name=args.model,
            **extra,
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
# Subcommand: agent (tool-calling loop)
# ---------------------------------------------------------------------------


def _cmd_agent(args, *, out, err) -> int:
    from src.local_agent.agent_loop import ToolCallingAgent, build_default_registry

    repo_root = Path(args.repo_root).expanduser().resolve()
    if not repo_root.is_dir():
        err.write(f"Error: repo-root is not a directory: {repo_root}\n")
        return 2

    llm = _OllamaAdapter(model_name=args.model, timeout=args.timeout)
    # Enable the RAG-backed search_code tool only when an index dir is given.
    registry = build_default_registry(
        repo_root,
        index_dir=args.index_dir,
        embed_model=args.embed_model if args.index_dir else None,
    )
    agent = ToolCallingAgent(llm, registry, max_iters=args.max_iters)

    # Load prior turns for this session, if one was requested.
    store, history = _load_session(args)

    try:
        result = agent.run(args.question, history=history)
    except ValueError as error:
        err.write(f"Error: {error}\n")
        return 2
    except Exception as error:
        err.write(f"Error: agent failed: {error}\n")
        if _debug_enabled(args.verbose):
            import traceback

            traceback.print_exc(file=err)
        return 1

    if args.verbose:
        out.write("Steps:\n")
        for i, step in enumerate(result.steps, start=1):
            preview = (step.tool_output or "").splitlines()[:1]
            snippet = f" -> {preview[0][:60]}" if preview else ""
            out.write(f"  {i}. {step.kind}: {step.detail[:60]}{snippet}\n")
        out.write(f"  (stopped: {result.stopped_reason})\n\n")

    # Persist this turn so the next `--session <same-id>` run remembers it.
    if store is not None and args.session:
        _save_turn(store, args.session, args.question, result.answer)

    out.write("Answer:\n")
    out.write(f"  {result.answer}\n")
    if result.warnings:
        out.write("\nGuardrail warnings:\n")
        for w in result.warnings:
            out.write(f"  ! {w}\n")
    return 0


def _load_session(args):
    """Return (store, history). Both are None/empty when no --session given."""
    if not args.session:
        return None, None
    from src.local_agent.memory.storage import SessionStore

    store = SessionStore(args.session_db)
    turns = store.load_turns(args.session, limit=args.history_turns)
    history = [(t.role, t.content) for t in turns]
    return store, history


def _save_turn(store, session_id: str, question: str, answer: str) -> None:
    from src.local_agent.memory.storage import Turn

    now = datetime.now(timezone.utc).isoformat()
    store.ensure_session(session_id, now=now)
    store.append_turn(session_id, Turn(role="user", content=question), now=now)
    store.append_turn(session_id, Turn(role="agent", content=answer), now=now)


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
        "",
        "Citations:",
    ]
    if response.citations:
        lines.extend(f"  - {c.to_text()}" for c in response.citations)
    else:
        lines.append("  (no source chunks were retrieved)")

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
    embed_model: str = DEFAULT_EMBED_MODEL,
    timeout: int = DEFAULT_LLM_TIMEOUT,
) -> LocalAgent:
    from src.local_agent.retrieval.context_builder import ContextBuilder
    from src.local_agent.retrieval.retriever import BasicRetriever

    # embed_model drives retrieval (must match the index); model_name is the LLM.
    retriever = BasicRetriever(index_dir=index_dir, model_name=embed_model)
    context_builder = ContextBuilder(
        max_tokens=config.max_context_tokens,
        reserve_tokens=config.reserve_tokens,
    )
    llm_client = _OllamaAdapter(model_name=model_name, timeout=timeout)
    return LocalAgent(
        retriever=retriever,
        context_builder=context_builder,
        llm_client=llm_client,
        config=config,
    )


class _OllamaAdapter:
    """Translate LLMClientProtocol(generate) → OllamaProvider(call(messages))."""

    def __init__(self, model_name: str, timeout: int = DEFAULT_LLM_TIMEOUT) -> None:
        self.model_name = model_name
        self.timeout = timeout
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
        result = provider.call(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=self.timeout,
        )
        if result is None:
            raise RuntimeError("Ollama returned no response (connection or timeout error)")
        return result


if __name__ == "__main__":
    sys.exit(main())
