"""
Context Builder (P0-08).

Convert a list[RetrievalResult] from P0-07 into a ContextWindow with a
deterministic, debug-friendly formatted_context, ready for prompt injection.

Scope: dedupe + budget enforcement + format. No reranking, no rewriting,
no LLM summarization, no new retrieval.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from src.local_agent.retrieval.retriever import RetrievalResult


def _approx_tokens(text: str) -> int:
    """Heuristic: ~4 chars per token. Min 1 to avoid zero-token chunks."""
    return max(1, len(text) // 4)


@dataclass(frozen=True)
class ContextMetadata:
    """Statistics about an assembled context window."""

    total_chunks: int
    total_tokens: int
    total_chars: int
    chunk_levels: dict[str, int]
    files_covered: list[str]
    assembly_time_ms: int
    timestamp: datetime


@dataclass(frozen=True)
class ContextWindow:
    """A formatted, budget-bounded context ready for prompt injection."""

    query: str
    chunks: list[RetrievalResult]
    formatted_context: str
    total_tokens: int
    metadata: ContextMetadata

    def to_prompt_fragment(self) -> str:
        """Return the formatted context for injection into an LLM prompt."""
        return self.formatted_context


class ContextBuilder:
    """Assembles RetrievalResults into a token-bounded ContextWindow."""

    def __init__(self, max_tokens: int = 32000, reserve_tokens: int = 4000) -> None:
        if max_tokens < 1:
            raise ValueError(f"max_tokens must be >= 1, got {max_tokens}")
        if reserve_tokens < 0:
            raise ValueError(f"reserve_tokens must be >= 0, got {reserve_tokens}")
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens

    def build(
        self,
        query: str,
        retrieval_results: list[RetrievalResult],
        max_tokens: int | None = None,
    ) -> ContextWindow:
        """Assemble retrieval results into a ContextWindow within token budget."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty, non-whitespace string")
        if not retrieval_results:
            raise ValueError("retrieval_results must not be empty")

        started = time.perf_counter()

        ordered = sorted(retrieval_results, key=lambda r: r.rank)

        seen_ids: set[str] = set()
        deduped: list[RetrievalResult] = []
        for result in ordered:
            if result.chunk_id in seen_ids:
                continue
            seen_ids.add(result.chunk_id)
            deduped.append(result)

        budget_source = max_tokens if max_tokens is not None else self.max_tokens
        effective_budget = max(1, budget_source - self.reserve_tokens)

        selected: list[RetrievalResult] = []
        running_tokens = 0
        for result in deduped:
            cost = _approx_tokens(result.content)
            if not selected:
                # Always include the first chunk, even if it overflows the budget.
                selected.append(result)
                running_tokens = cost
                continue
            if running_tokens + cost > effective_budget:
                break
            selected.append(result)
            running_tokens += cost

        formatted = _format_context(query=query, chunks=selected)

        files_covered = _unique_preserve_order(
            (r.relative_path or r.file_path) for r in selected
        )
        levels = dict(Counter(r.level for r in selected))
        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))

        metadata = ContextMetadata(
            total_chunks=len(selected),
            total_tokens=running_tokens,
            total_chars=sum(len(r.content) for r in selected),
            chunk_levels=levels,
            files_covered=files_covered,
            assembly_time_ms=elapsed_ms,
            timestamp=datetime.now(timezone.utc),
        )

        return ContextWindow(
            query=query,
            chunks=selected,
            formatted_context=formatted,
            total_tokens=running_tokens,
            metadata=metadata,
        )


def _format_context(query: str, chunks: list[RetrievalResult]) -> str:
    lines: list[str] = [f"Query: {query}", ""]
    for index, chunk in enumerate(chunks, start=1):
        lines.append(f"[Chunk {index}]")
        lines.append(f"File: {chunk.file_path}")
        if chunk.relative_path:
            lines.append(f"Relative Path: {chunk.relative_path}")
        if chunk.qualified_name:
            lines.append(f"Qualified Name: {chunk.qualified_name}")
        elif chunk.name:
            lines.append(f"Name: {chunk.name}")
        lines.append(f"Level: {chunk.level}")
        lines.append(f"Lines: {chunk.start_line}-{chunk.end_line}")
        lines.append(f"Score: {chunk.score:.4f}")
        if chunk.docstring:
            lines.append("Docstring:")
            lines.append(chunk.docstring)
        lines.append("Code:")
        lines.append(chunk.content)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


__all__ = ["ContextBuilder", "ContextMetadata", "ContextWindow"]
