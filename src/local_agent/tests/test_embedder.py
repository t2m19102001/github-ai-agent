"""
Embedder tests via the legacy `indexing.embedder` import path.

After P1 cleanup, `src/local_agent/indexing/embedder.py` is a thin
compatibility wrapper. Canonical implementation lives at
`src/local_agent/ingestion/embedder.py`. These tests:

* lock the legacy import path so existing callers don't break;
* verify canonical behavior is reachable through both paths; and
* provide the 3 compatibility regressions required by the cleanup spec.
"""

from __future__ import annotations

import hashlib

import pytest

from src.local_agent.indexing import embedder as legacy_embedder
from src.local_agent.indexing.embedder import (
    DEFAULT_MODEL_NAME,
    EmbeddedChunk,
    Embedder,
    embed_chunks,
    to_embed_text,
)
from src.local_agent.ingestion import embedder as canonical_embedder
from src.local_agent.ingestion.chunker import ChunkLevel, CodeChunk


_DIM = 4


class _FakeModel:
    """Deterministic, dependency-free stand-in for SentenceTransformer."""

    def get_sentence_embedding_dimension(self) -> int:
        return _DIM

    def eval(self) -> None:
        return None

    def encode(self, texts, batch_size: int, **_):
        import numpy as np

        rows = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            rows.append([digest[i] / 255.0 for i in range(_DIM)])
        return np.asarray(rows, dtype="float32")


@pytest.fixture
def fake_model(monkeypatch) -> _FakeModel:
    pytest.importorskip("numpy")
    fake = _FakeModel()
    monkeypatch.setattr(
        Embedder,
        "_load_model",
        lambda self: setattr(self, "_model", fake) or fake,
    )
    return fake


def _build_chunk(chunk_id: str = "chunk-1", content: str = "sample content") -> CodeChunk:
    return CodeChunk(
        id=chunk_id,
        level=ChunkLevel.FUNCTION,
        file_path="/tmp/sample.py",
        relative_path="sample.py",
        name="alpha",
        qualified_name="alpha",
        start_line=1,
        end_line=2,
        content=content,
        docstring="sample docstring",
        imports=[],
        symbols=["alpha"],
        parent_name=None,
        metadata={},
        token_count=None,
    )


# ---------------------------------------------------------------------------
# Required compatibility regression tests
# ---------------------------------------------------------------------------


def test_embedder_import_compatibility() -> None:
    """Legacy import path must still resolve."""
    from src.local_agent.indexing.embedder import (  # noqa: F401
        DEFAULT_MODEL_NAME,
        EmbeddedChunk,
        Embedder,
        embed_chunks,
        to_embed_text,
    )
    # And via the indexing package re-export.
    from src.local_agent.indexing import EmbeddedChunk as ReexportEmbeddedChunk  # noqa: F401
    from src.local_agent.indexing import Embedder as ReexportEmbedder  # noqa: F401


def test_embedder_same_api_surface() -> None:
    """Legacy path resolves to the canonical objects, not duplicates."""
    assert legacy_embedder.Embedder is canonical_embedder.Embedder
    assert legacy_embedder.EmbeddedChunk is canonical_embedder.EmbeddedChunk
    assert legacy_embedder.to_embed_text is canonical_embedder.to_embed_text
    assert legacy_embedder.embed_chunks is canonical_embedder.embed_chunks
    assert legacy_embedder.DEFAULT_MODEL_NAME == canonical_embedder.DEFAULT_MODEL_NAME


def test_embedder_pipeline_still_works(fake_model, tmp_path) -> None:
    """End-to-end: chunk → embed (legacy import) → IndexBuilder.build → load."""
    pytest.importorskip("faiss")
    from src.local_agent.indexing.index_builder import IndexBuilder

    chunks = [_build_chunk("a"), _build_chunk("b")]
    embedded = Embedder(model_name="fake-model").embed(chunks)
    result = IndexBuilder(tmp_path).build(embedded)
    assert result.total_chunks == 2

    index, metadata = IndexBuilder.load(tmp_path)
    assert index.ntotal == 2
    assert {m.chunk_id for m in metadata} == {"a", "b"}


# ---------------------------------------------------------------------------
# Canonical behavior locked through the legacy import path
# ---------------------------------------------------------------------------


def test_to_embed_text_returns_content_unchanged() -> None:
    chunk = _build_chunk(content="line one\nline two")
    assert to_embed_text(chunk) == "line one\nline two"


def test_to_embed_text_passes_through_empty_content() -> None:
    """Canonical contract: no fallback. Empty content stays empty."""
    chunk = _build_chunk(content="")
    assert to_embed_text(chunk) == ""


def test_default_model_name_constant() -> None:
    assert DEFAULT_MODEL_NAME == "all-MiniLM-L6-v2"


def test_embed_returns_one_embedded_chunk_per_input(fake_model) -> None:
    chunks = [_build_chunk(f"c{i}", f"content {i}") for i in range(3)]
    out = Embedder(model_name="fake-model").embed(chunks)
    assert len(out) == 3
    assert all(isinstance(item, EmbeddedChunk) for item in out)


def test_embedding_is_list_of_float(fake_model) -> None:
    chunk = _build_chunk()
    [embedded] = Embedder(model_name="fake-model").embed([chunk])
    assert isinstance(embedded.embedding, list)
    assert all(isinstance(v, float) for v in embedded.embedding)
    assert embedded.embedding_dim == _DIM


def test_deterministic_same_chunk_same_vector(fake_model) -> None:
    chunk = _build_chunk(content="stable content")
    [a] = Embedder(model_name="fake-model").embed([chunk])
    [b] = Embedder(model_name="fake-model").embed([chunk])
    assert a.embedding == b.embedding


def test_model_name_propagates_into_embedded_chunk(fake_model) -> None:
    chunk = _build_chunk()
    [embedded] = Embedder(model_name="custom-model").embed([chunk])
    assert embedded.model_name == "custom-model"


def test_embedded_chunk_preserves_chunk_id(fake_model) -> None:
    chunk = _build_chunk(chunk_id="zzz-id")
    [embedded] = Embedder(model_name="fake-model").embed([chunk])
    assert embedded.chunk_id == "zzz-id"
    assert embedded.chunk is chunk


def test_embed_chunks_functional_api_works(fake_model) -> None:
    chunks = [_build_chunk("a"), _build_chunk("b")]
    out = embed_chunks(chunks, model_name="fake-model")
    assert [e.chunk_id for e in out] == ["a", "b"]


def test_empty_input_returns_empty_list(fake_model) -> None:
    assert Embedder(model_name="fake-model").embed([]) == []


def test_invalid_batch_size_rejected() -> None:
    with pytest.raises(ValueError):
        Embedder(batch_size=0)
