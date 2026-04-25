"""P0-07 Basic Retriever tests.

The Embedder is monkey-patched with a deterministic, in-memory model so
the test suite stays hermetic and fast. The model maps every input string
to a 4-dim sha256-derived vector — same hashing the embedder tests use,
keeping FAISS distances reproducible without downloading weights.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

faiss = pytest.importorskip("faiss", reason="faiss-cpu is required for retriever tests")
np = pytest.importorskip("numpy", reason="numpy is required for retriever tests")

from src.local_agent.indexing.index_builder import IndexBuilder
from src.local_agent.ingestion.chunker import ChunkLevel, CodeChunk
from src.local_agent.ingestion.embedder import EmbeddedChunk, Embedder
from src.local_agent.retrieval.retriever import (
    BasicRetriever,
    RetrievalResult,
    RetrievalSource,
)


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


def _make_chunk(chunk_id: str) -> CodeChunk:
    return CodeChunk(
        id=chunk_id,
        level=ChunkLevel.FUNCTION,
        file_path=f"/repo/{chunk_id}.py",
        relative_path=f"{chunk_id}.py",
        name=chunk_id,
        qualified_name=chunk_id,
        start_line=10,
        end_line=20,
        content=f"content for {chunk_id}",
        docstring=f"doc {chunk_id}",
        imports=[],
        symbols=[chunk_id],
        parent_name=None,
        metadata={},
        token_count=None,
    )


def _embed_text(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [digest[i] / 255.0 for i in range(_DIM)]


def _make_embedded(chunk_id: str, text: str | None = None) -> EmbeddedChunk:
    embedding = _embed_text(text if text is not None else f"content for {chunk_id}")
    return EmbeddedChunk(
        chunk_id=chunk_id,
        embedding=embedding,
        model_name=_MODEL,
        embedding_dim=_DIM,
        chunk=_make_chunk(chunk_id),
    )


def _build_index(tmp_path: Path, chunk_ids: list[str]) -> Path:
    index_dir = tmp_path / "index"
    chunks = [_make_embedded(cid) for cid in chunk_ids]
    IndexBuilder(index_dir).build(chunks)
    return index_dir


# 1. Retrieve top-k succeeds.
def test_retrieve_returns_results(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["a", "b", "c", "d"])
    retriever = BasicRetriever(index_dir, model_name=_MODEL)
    results = retriever.retrieve("content for a", k=2)
    assert results, "expected at least one result"
    assert all(isinstance(r, RetrievalResult) for r in results)


# 2. Returns exactly k when index has enough.
def test_retrieve_returns_k_when_index_large_enough(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["a", "b", "c", "d", "e"])
    results = BasicRetriever(index_dir, model_name=_MODEL).retrieve("content for a", k=3)
    assert len(results) == 3


# 3. Returns fewer than k when index is smaller.
def test_retrieve_caps_at_index_size(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["a", "b"])
    results = BasicRetriever(index_dir, model_name=_MODEL).retrieve("content for a", k=10)
    assert len(results) == 2


# 4. Rank starts at 1 and increments.
def test_rank_is_one_indexed_and_monotonic(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["a", "b", "c", "d"])
    results = BasicRetriever(index_dir, model_name=_MODEL).retrieve("content for a", k=4)
    assert [r.rank for r in results] == list(range(1, len(results) + 1))


# 5. metadata[faiss_id] mapping is correct (top hit on exact-match query).
def test_top_hit_matches_expected_chunk(tmp_path: Path) -> None:
    # Insert order != sorted order. P0-06 sorts by chunk.id, so:
    #   FAISS_ID 0 -> alpha, 1 -> beta, 2 -> zeta.
    # Querying for "zeta" must hit FAISS_ID=2; a buggy `metadata[0]` mapping
    # would wrongly return "alpha".
    index_dir = _build_index(tmp_path, ["zeta", "beta", "alpha"])
    retriever = BasicRetriever(index_dir, model_name=_MODEL)
    results = retriever.retrieve("content for zeta", k=1)
    assert results[0].chunk_id == "zeta"
    assert results[0].score == pytest.approx(0.0, abs=1e-5)


# 6. Empty / whitespace query raises ValueError.
@pytest.mark.parametrize("bad_query", ["", "   ", "\n\t"])
def test_empty_query_raises(tmp_path: Path, bad_query: str) -> None:
    index_dir = _build_index(tmp_path, ["a", "b"])
    retriever = BasicRetriever(index_dir, model_name=_MODEL)
    with pytest.raises(ValueError):
        retriever.retrieve(bad_query)


# 7. Missing index raises FileNotFoundError.
def test_missing_index_raises(tmp_path: Path) -> None:
    retriever = BasicRetriever(tmp_path / "nope", model_name=_MODEL)
    with pytest.raises(FileNotFoundError):
        retriever.retrieve("anything")


# 8. Empty index returns [] without crashing.
def test_empty_index_returns_empty_list(tmp_path: Path) -> None:
    index_dir = tmp_path / "empty"
    IndexBuilder(index_dir).build([])
    results = BasicRetriever(index_dir, model_name=_MODEL).retrieve("query", k=5)
    assert results == []


# 9. Batch retrieve returns one list per input query, in order.
def test_batch_retrieve_preserves_order(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["alpha", "beta", "gamma"])
    retriever = BasicRetriever(index_dir, model_name=_MODEL)
    queries = ["content for beta", "content for gamma", "content for alpha"]
    batched = retriever.batch_retrieve(queries, k=1)
    assert len(batched) == 3
    assert [hits[0].chunk_id for hits in batched] == ["beta", "gamma", "alpha"]


# 10. Deterministic across calls.
def test_retrieve_is_deterministic(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["a", "b", "c", "d", "e"])
    retriever = BasicRetriever(index_dir, model_name=_MODEL)
    a = retriever.retrieve("content for c", k=4)
    b = retriever.retrieve("content for c", k=4)
    assert [r.chunk_id for r in a] == [r.chunk_id for r in b]
    assert [r.score for r in a] == [r.score for r in b]


# 11. source is RetrievalSource.DENSE for every result.
def test_source_is_dense_for_all_hits(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["a", "b", "c"])
    results = BasicRetriever(index_dir, model_name=_MODEL).retrieve("content for a", k=3)
    assert all(r.source == RetrievalSource.DENSE for r in results)


# 12. Metadata round-trips correctly into the result.
def test_metadata_fields_preserved(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["alpha"])
    result = BasicRetriever(index_dir, model_name=_MODEL).retrieve("content for alpha", k=1)[0]
    assert result.file_path == "/repo/alpha.py"
    assert result.relative_path == "alpha.py"
    assert result.start_line == 10
    assert result.end_line == 20
    assert result.content == "content for alpha"
    assert result.docstring == "doc alpha"
    assert result.level == ChunkLevel.FUNCTION.value
    assert result.symbols == ["alpha"]


# Bonus: invalid k.
def test_invalid_k_raises(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["a"])
    retriever = BasicRetriever(index_dir, model_name=_MODEL)
    with pytest.raises(ValueError):
        retriever.retrieve("query", k=0)


# Bonus (M-2): model-name mismatch must fail loudly, not silently return garbage.
def test_model_name_mismatch_raises(tmp_path: Path) -> None:
    index_dir = _build_index(tmp_path, ["a", "b"])  # built with _MODEL = "fake-model"
    retriever = BasicRetriever(index_dir, model_name="some-other-model")
    with pytest.raises(ValueError, match="Model mismatch"):
        retriever.retrieve("query")
