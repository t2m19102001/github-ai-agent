"""Tests for HybridRetriever (dense FAISS + BM25 fused via RRF).

Reuses the hermetic fake-embedder pattern from test_retriever so no model
weights are downloaded and FAISS distances stay reproducible.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

faiss = pytest.importorskip("faiss", reason="faiss-cpu required")
np = pytest.importorskip("numpy", reason="numpy required")

from src.local_agent.indexing.index_builder import IndexBuilder
from src.local_agent.ingestion.chunker import ChunkLevel, CodeChunk
from src.local_agent.ingestion.embedder import EmbeddedChunk, Embedder
from src.local_agent.retrieval.hybrid import HybridRetriever
from src.local_agent.retrieval.retriever import RetrievalSource

_DIM = 4
_MODEL = "fake-model"


class _FakeModel:
    def get_sentence_embedding_dimension(self) -> int:
        return _DIM

    def eval(self) -> None:
        return None

    def encode(self, texts, batch_size: int, **_):
        rows = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            rows.append([digest[i] / 255.0 for i in range(_DIM)])
        return np.asarray(rows, dtype="float32")


@pytest.fixture(autouse=True)
def _patch_embedder(monkeypatch):
    fake = _FakeModel()
    monkeypatch.setattr(
        Embedder,
        "_load_model",
        lambda self: setattr(self, "_model", fake) or fake,
    )
    return fake


def _embed(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [digest[i] / 255.0 for i in range(_DIM)]


def _embedded(chunk_id: str, content: str) -> EmbeddedChunk:
    chunk = CodeChunk(
        id=chunk_id,
        level=ChunkLevel.FUNCTION,
        file_path=f"/repo/{chunk_id}.py",
        relative_path=f"{chunk_id}.py",
        name=chunk_id,
        qualified_name=chunk_id,
        start_line=1,
        end_line=5,
        content=content,
        docstring=None,
        imports=[],
        symbols=[chunk_id],
        parent_name=None,
        metadata={},
        token_count=None,
    )
    return EmbeddedChunk(
        chunk_id=chunk_id,
        embedding=_embed(content),
        model_name=_MODEL,
        embedding_dim=_DIM,
        chunk=chunk,
    )


def _build(tmp_path: Path, items: list[tuple[str, str]]) -> Path:
    index_dir = tmp_path / "index"
    IndexBuilder(index_dir).build([_embedded(cid, content) for cid, content in items])
    return index_dir


def test_hybrid_returns_results_marked_hybrid(tmp_path: Path) -> None:
    index_dir = _build(
        tmp_path,
        [
            ("a", "database connection pool"),
            ("b", "authentication login flow"),
            ("c", "the cat sat on the mat"),
        ],
    )
    retr = HybridRetriever(index_dir, model_name=_MODEL)
    results = retr.retrieve("database connection", k=3)
    assert results
    assert all(r.source == RetrievalSource.HYBRID for r in results)


def test_hybrid_surfaces_keyword_match_bm25_finds(tmp_path: Path) -> None:
    # An exact rare keyword should be retrievable via the BM25 half even when
    # the fake dense vectors don't cluster it near the query.
    index_dir = _build(
        tmp_path,
        [
            ("x", "handles zzqspecialtoken parsing"),
            ("y", "generic helper utilities"),
            ("z", "more generic helper code"),
        ],
    )
    retr = HybridRetriever(index_dir, model_name=_MODEL)
    ids = [r.chunk_id for r in retr.retrieve("zzqspecialtoken", k=3)]
    assert "x" in ids


def test_hybrid_ranks_are_sequential(tmp_path: Path) -> None:
    index_dir = _build(
        tmp_path,
        [("a", "alpha one"), ("b", "beta two"), ("c", "gamma three")],
    )
    results = HybridRetriever(index_dir, model_name=_MODEL).retrieve("alpha", k=3)
    assert [r.rank for r in results] == list(range(1, len(results) + 1))


def test_hybrid_rejects_empty_query(tmp_path: Path) -> None:
    index_dir = _build(tmp_path, [("a", "content")])
    with pytest.raises(ValueError):
        HybridRetriever(index_dir, model_name=_MODEL).retrieve("   ", k=3)


def test_hybrid_respects_k(tmp_path: Path) -> None:
    index_dir = _build(
        tmp_path, [(f"c{i}", f"shared token c{i}") for i in range(6)]
    )
    results = HybridRetriever(index_dir, model_name=_MODEL).retrieve("shared", k=2)
    assert len(results) == 2
