"""
Hybrid retriever — fuse dense (FAISS) and sparse (BM25) rankings.

Dense retrieval matches meaning; BM25 matches exact tokens. Each alone misses
cases the other catches, so we run both and merge with Reciprocal Rank Fusion
(RRF):

    fused_score(doc) = sum over rankers of  1 / (rrf_k + rank_in_that_ranker)

RRF fuses by *rank position*, not by raw score, so we don't have to reconcile
FAISS L2 distances with BM25 magnitudes — a well-known, dependency-free trick.
A doc ranked highly by either signal (or moderately by both) floats to the top.

The retriever exposes the same ``retrieve(query, k)`` shape as BasicRetriever,
so it drops into LocalAgent unchanged.
"""

from __future__ import annotations

from pathlib import Path

from src.local_agent.indexing.index_builder import IndexBuilder, IndexMetadata
from src.local_agent.ingestion.embedder import DEFAULT_MODEL_NAME
from src.local_agent.retrieval.retriever import (
    BasicRetriever,
    RetrievalResult,
    RetrievalSource,
    _to_result,
)
from src.local_agent.retrieval.sparse import BM25Index

_RRF_K = 60  # standard RRF constant; larger = flatter rank weighting


class HybridRetriever:
    """Dense + BM25 retrieval merged with Reciprocal Rank Fusion."""

    def __init__(
        self,
        index_dir: str | Path,
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        self.index_dir = Path(index_dir).expanduser()
        self.model_name = model_name
        self._dense = BasicRetriever(index_dir=index_dir, model_name=model_name)
        self._metadata: list[IndexMetadata] | None = None
        self._bm25: BM25Index | None = None

    def _load_sparse(self) -> tuple[list[IndexMetadata], BM25Index]:
        if self._metadata is None or self._bm25 is None:
            _, metadata = IndexBuilder.load(self.index_dir)
            self._metadata = metadata
            self._bm25 = BM25Index([m.content for m in metadata])
        return self._metadata, self._bm25

    def retrieve(self, query: str, k: int = 10) -> list[RetrievalResult]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty, non-whitespace string")
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")

        # Pull a wider candidate pool from each signal, then fuse and trim to k.
        pool = max(k * 4, 20)
        dense_hits = self._dense.retrieve(query, k=pool)

        metadata, bm25 = self._load_sparse()
        sparse_hits = bm25.top_k(query, k=pool)  # list[(meta_index, score)]

        # Rank maps: chunk_id -> rank (1-based) in each ranker.
        dense_rank = {r.chunk_id: i + 1 for i, r in enumerate(dense_hits)}
        sparse_rank = {
            metadata[idx].chunk_id: i + 1
            for i, (idx, _score) in enumerate(sparse_hits)
        }

        fused = _reciprocal_rank_fusion(dense_rank, sparse_rank)

        # Rebuild RetrievalResult objects for the top-k fused chunk_ids.
        by_id = {m.chunk_id: m for m in metadata}
        results: list[RetrievalResult] = []
        for rank, (chunk_id, fused_score) in enumerate(fused[:k], start=1):
            meta = by_id.get(chunk_id)
            if meta is None:
                continue
            result = _to_result(meta, score=fused_score, rank=rank)
            # Mark provenance as hybrid so downstream can tell how it was found.
            results.append(_with_source(result, RetrievalSource.HYBRID))
        return results


def _reciprocal_rank_fusion(
    dense_rank: dict[str, int],
    sparse_rank: dict[str, int],
) -> list[tuple[str, float]]:
    """Merge two rank maps into one list of (chunk_id, score), best first."""
    scores: dict[str, float] = {}
    for ranks in (dense_rank, sparse_rank):
        for chunk_id, rank in ranks.items():
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)


def _with_source(result: RetrievalResult, source: RetrievalSource) -> RetrievalResult:
    """Return a copy of ``result`` with a different provenance source."""
    from dataclasses import replace

    return replace(result, source=source)


__all__ = ["HybridRetriever"]
