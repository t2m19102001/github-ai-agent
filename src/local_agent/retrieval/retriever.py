"""
Basic Retriever (P0-07).

Top-k dense retrieval over a FAISS index built by P0-06. Embeds the user
query with the same Embedder used at index time and looks up nearest
neighbours via L2 distance, mapping FAISS row IDs to IndexMetadata records.

Score semantics:
    `RetrievalResult.score` is the raw FAISS L2 distance. Lower is better.
    Downstream consumers (P0-08 ContextBuilder) may transform this if they
    need a similarity-style 0..1 score; the retriever does not.

FAISS-ID mapping contract:
    P0-06 sorts chunks by `chunk.id` before insertion, so:
        FAISS row N  <->  metadata[N]
    The retriever assumes nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from src.local_agent.indexing.index_builder import IndexBuilder, IndexMetadata
from src.local_agent.ingestion.embedder import DEFAULT_MODEL_NAME, Embedder

if TYPE_CHECKING:
    import faiss
    import numpy as np


class RetrievalSource(str, Enum):
    """Which retrieval signal produced this hit. V1 only has dense."""

    DENSE = "dense"


@dataclass(frozen=True)
class RetrievalResult:
    """A single ranked hit ready to feed into the context builder."""

    chunk_id: str
    file_path: str
    relative_path: str | None
    name: str | None
    qualified_name: str | None
    level: str
    start_line: int
    end_line: int
    content: str
    docstring: str | None
    symbols: list[str]
    parent_name: str | None
    score: float
    rank: int
    source: RetrievalSource


class BasicRetriever:
    """Dense top-k retriever backed by a FAISS IndexFlatL2."""

    def __init__(
        self,
        index_dir: str | Path,
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        self.index_dir = Path(index_dir).expanduser()
        self.model_name = model_name
        self._embedder = Embedder(model_name=model_name)
        self._index: faiss.Index | None = None
        self._metadata: list[IndexMetadata] | None = None

    def _load(self) -> tuple[faiss.Index, list[IndexMetadata]]:
        if self._index is None or self._metadata is None:
            index, metadata = IndexBuilder.load(self.index_dir)
            if metadata and metadata[0].model_name != self.model_name:
                raise ValueError(
                    f"Model mismatch: index was built with {metadata[0].model_name!r}, "
                    f"retriever configured with {self.model_name!r}. "
                    f"Pass model_name={metadata[0].model_name!r} or rebuild the index."
                )
            self._index = index
            self._metadata = metadata
        return self._index, self._metadata

    def retrieve(self, query: str, k: int = 10) -> list[RetrievalResult]:
        """Return up to `k` nearest chunks, ranked by ascending L2 distance."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty, non-whitespace string")
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")

        index, metadata = self._load()
        if index.ntotal == 0:
            return []

        import numpy as np

        embedding = self._embedder.encode_text([query])[0]
        query_vec = np.asarray([embedding], dtype="float32")
        effective_k = min(k, index.ntotal)
        distances, indices = index.search(query_vec, effective_k)

        results: list[RetrievalResult] = []
        rank = 1
        for raw_id, distance in zip(indices[0], distances[0]):
            faiss_id = int(raw_id)
            if faiss_id < 0:
                continue
            if faiss_id >= len(metadata):
                continue  # defensive: corrupt sidecar, skip rather than crash
            results.append(_to_result(metadata[faiss_id], score=float(distance), rank=rank))
            rank += 1
        return results

    def batch_retrieve(
        self, queries: list[str], k: int = 10
    ) -> list[list[RetrievalResult]]:
        """Run `retrieve` for each query; preserves input order."""
        return [self.retrieve(query, k=k) for query in queries]


def _to_result(meta: IndexMetadata, score: float, rank: int) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=meta.chunk_id,
        file_path=meta.file_path,
        relative_path=meta.relative_path,
        name=meta.name,
        qualified_name=meta.qualified_name,
        level=meta.level,
        start_line=meta.start_line,
        end_line=meta.end_line,
        content=meta.content,
        docstring=meta.docstring,
        symbols=list(meta.symbols),
        parent_name=meta.parent_name,
        score=score,
        rank=rank,
        source=RetrievalSource.DENSE,
    )


__all__ = [
    "BasicRetriever",
    "RetrievalResult",
    "RetrievalSource",
]
