"""P0-05 Embedder tests.

These tests use a deterministic in-memory fake model so they don't require
the heavyweight `sentence-transformers` download. The contract under test
is the `Embedder` adapter, not the upstream SentenceTransformer library.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

import pytest

from src.local_agent.ingestion.chunker import ChunkLevel, CodeChunk, chunk_file
from src.local_agent.ingestion.embedder import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MODEL_NAME,
    EmbeddedChunk,
    Embedder,
    embed_chunks,
    to_embed_text,
)
from src.local_agent.ingestion.parser import parse_file
from src.local_agent.ingestion.symbols import extract_symbols


_FAKE_DIM = 8


class _FakeModel:
    """Deterministic stand-in for SentenceTransformer."""

    def __init__(self, dim: int = _FAKE_DIM) -> None:
        self._dim = dim
        self.encode_calls: list[list[str]] = []

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim

    def eval(self) -> None:  # pragma: no cover - no-op
        return None

    def encode(self, texts, batch_size: int, **_: object):
        import numpy as np

        self.encode_calls.append(list(texts))
        rows = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            row = [digest[i] / 255.0 for i in range(self._dim)]
            rows.append(row)
        return np.asarray(rows, dtype="float32")


def _make_chunk(chunk_id: str, content: str) -> CodeChunk:
    return CodeChunk(
        id=chunk_id,
        level=ChunkLevel.FUNCTION,
        file_path="/tmp/x.py",
        relative_path="x.py",
        name="fn",
        qualified_name="fn",
        start_line=1,
        end_line=2,
        content=content,
        docstring=None,
        imports=[],
        symbols=[],
        parent_name=None,
        metadata={},
        token_count=None,
    )


def _embedder_with_fake() -> tuple[Embedder, _FakeModel]:
    fake = _FakeModel()
    emb = Embedder(model_name="fake-model", batch_size=4)
    emb._model = fake  # type: ignore[attr-defined]  # bypass lazy load
    return emb, fake


def test_to_embed_text_returns_content_unchanged() -> None:
    chunk = _make_chunk("c1", "hello world\nbody")
    assert to_embed_text(chunk) == "hello world\nbody"


def test_default_constants_match_config() -> None:
    assert DEFAULT_MODEL_NAME == "all-MiniLM-L6-v2"
    assert DEFAULT_BATCH_SIZE == 32


def test_embedder_rejects_invalid_batch_size() -> None:
    with pytest.raises(ValueError):
        Embedder(batch_size=0)


def test_empty_input_returns_empty_list() -> None:
    pytest.importorskip("numpy")
    emb, _ = _embedder_with_fake()
    assert emb.embed([]) == []


def test_embed_produces_expected_shape() -> None:
    pytest.importorskip("numpy")
    emb, _ = _embedder_with_fake()
    chunks = [_make_chunk(f"c{i}", f"text-{i}") for i in range(3)]
    out = emb.embed(chunks)
    assert len(out) == 3
    for embedded, source in zip(out, chunks):
        assert isinstance(embedded, EmbeddedChunk)
        assert embedded.chunk_id == source.id
        assert embedded.model_name == "fake-model"
        assert embedded.embedding_dim == _FAKE_DIM
        assert len(embedded.embedding) == _FAKE_DIM
        assert all(isinstance(v, float) for v in embedded.embedding)
        assert embedded.chunk is source


def test_embed_preserves_input_order() -> None:
    pytest.importorskip("numpy")
    emb, _ = _embedder_with_fake()
    chunks = [_make_chunk(f"c{i}", f"text-{i}") for i in range(5)]
    out = emb.embed(chunks)
    assert [e.chunk_id for e in out] == [c.id for c in chunks]


def test_embed_is_deterministic() -> None:
    pytest.importorskip("numpy")
    emb_a, _ = _embedder_with_fake()
    emb_b, _ = _embedder_with_fake()
    chunks = [_make_chunk(f"c{i}", f"content-{i}") for i in range(4)]
    out_a = emb_a.embed(chunks)
    out_b = emb_b.embed(chunks)
    assert [e.embedding for e in out_a] == [e.embedding for e in out_b]


def test_embed_uses_chunk_content_as_input_text() -> None:
    pytest.importorskip("numpy")
    emb, fake = _embedder_with_fake()
    chunks = [_make_chunk("c1", "ALPHA"), _make_chunk("c2", "BETA")]
    emb.embed(chunks)
    assert fake.encode_calls == [["ALPHA", "BETA"]]


def test_functional_api_smoke(monkeypatch) -> None:
    pytest.importorskip("numpy")
    fake = _FakeModel()

    def fake_load(self):  # type: ignore[no-untyped-def]
        self._model = fake
        return fake

    monkeypatch.setattr(Embedder, "_load_model", fake_load)
    chunks = [_make_chunk("c1", "x")]
    out = embed_chunks(chunks, model_name="fake")
    assert len(out) == 1
    assert out[0].embedding_dim == _FAKE_DIM


def test_pipeline_parse_to_embed(monkeypatch, sample_file: Path) -> None:
    """Integration: full ingestion → chunk → embed flow with fake model."""
    pytest.importorskip("numpy")
    fake = _FakeModel()
    monkeypatch.setattr(Embedder, "_load_model", lambda self: setattr(self, "_model", fake) or fake)

    pf = parse_file(sample_file)
    chunks = chunk_file(pf, extract_symbols(pf))
    embedded = embed_chunks(chunks, model_name="fake-pipeline")
    assert len(embedded) == len(chunks)
    assert all(len(e.embedding) == _FAKE_DIM for e in embedded)
    assert {e.chunk_id for e in embedded} == {c.id for c in chunks}
