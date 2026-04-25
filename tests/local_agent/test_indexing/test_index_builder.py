"""P0-06 FAISS Index Builder tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

faiss = pytest.importorskip("faiss", reason="faiss-cpu is required for IndexBuilder tests")
np = pytest.importorskip("numpy", reason="numpy is required for IndexBuilder tests")

from src.local_agent.indexing.index_builder import (
    INDEX_FILENAME,
    METADATA_FILENAME,
    IndexBuilder,
    IndexBuildResult,
    IndexMetadata,
)
from src.local_agent.ingestion.chunker import ChunkLevel, CodeChunk
from src.local_agent.ingestion.embedder import EmbeddedChunk


_DIM = 4
_MODEL = "test-model"


def _make_chunk(chunk_id: str, *, name: str = "fn") -> CodeChunk:
    return CodeChunk(
        id=chunk_id,
        level=ChunkLevel.FUNCTION,
        file_path=f"/repo/{chunk_id}.py",
        relative_path=f"{chunk_id}.py",
        name=name,
        qualified_name=name,
        start_line=1,
        end_line=10,
        content=f"content for {chunk_id}",
        docstring=f"doc for {chunk_id}",
        imports=[],
        symbols=[name],
        parent_name=None,
        metadata={},
        token_count=None,
    )


def _make_embedded(chunk_id: str, vector: list[float] | None = None) -> EmbeddedChunk:
    if vector is None:
        seed = sum(ord(c) for c in chunk_id)
        vector = [float((seed + i) % 7) for i in range(_DIM)]
    return EmbeddedChunk(
        chunk_id=chunk_id,
        embedding=vector,
        model_name=_MODEL,
        embedding_dim=_DIM,
        chunk=_make_chunk(chunk_id),
    )


def _sample_batch() -> list[EmbeddedChunk]:
    # Intentionally unsorted to verify deterministic ordering by chunk.id.
    return [
        _make_embedded("c-banana"),
        _make_embedded("c-apple"),
        _make_embedded("c-cherry"),
    ]


# 1. Build succeeds.
def test_build_returns_result(tmp_path: Path) -> None:
    builder = IndexBuilder(tmp_path)
    result = builder.build(_sample_batch())
    assert isinstance(result, IndexBuildResult)
    assert result.model_name == _MODEL


# 2. Both files exist on disk.
def test_build_writes_index_and_metadata(tmp_path: Path) -> None:
    builder = IndexBuilder(tmp_path)
    builder.build(_sample_batch())
    assert (tmp_path / INDEX_FILENAME).is_file()
    assert (tmp_path / METADATA_FILENAME).is_file()


# 3. total_chunks correct.
def test_total_chunks_matches_input(tmp_path: Path) -> None:
    chunks = _sample_batch()
    result = IndexBuilder(tmp_path).build(chunks)
    assert result.total_chunks == len(chunks)


# 4. embedding_dim derived from first vector.
def test_embedding_dim_matches_first_embedding(tmp_path: Path) -> None:
    chunks = _sample_batch()
    result = IndexBuilder(tmp_path).build(chunks)
    assert result.embedding_dim == _DIM
    assert result.embedding_dim == len(chunks[0].embedding)


# 5. Load returns FAISS index + metadata.
def test_load_returns_index_and_metadata(tmp_path: Path) -> None:
    builder = IndexBuilder(tmp_path)
    builder.build(_sample_batch())
    index, metadata = IndexBuilder.load(tmp_path)
    assert index.ntotal == 3
    assert all(isinstance(m, IndexMetadata) for m in metadata)


# 6. metadata count matches total_chunks.
def test_metadata_length_matches_total_chunks(tmp_path: Path) -> None:
    chunks = _sample_batch()
    result = IndexBuilder(tmp_path).build(chunks)
    _, metadata = IndexBuilder.load(tmp_path)
    assert len(metadata) == result.total_chunks


# 7. Metadata records carry the required fields.
def test_metadata_contains_required_fields(tmp_path: Path) -> None:
    IndexBuilder(tmp_path).build(_sample_batch())
    _, metadata = IndexBuilder.load(tmp_path)
    record = metadata[0]
    assert record.chunk_id
    assert record.file_path
    assert record.relative_path
    assert record.level == ChunkLevel.FUNCTION.value
    assert record.start_line == 1
    assert record.end_line == 10
    assert record.content.startswith("content for")
    assert record.docstring is not None
    assert record.model_name == _MODEL


# 8. exists() flips after build.
def test_exists_flips_after_build(tmp_path: Path) -> None:
    builder = IndexBuilder(tmp_path)
    assert builder.exists() is False
    builder.build(_sample_batch())
    assert builder.exists() is True


# 9. Deterministic: same input → same metadata order.
def test_build_is_deterministic(tmp_path: Path) -> None:
    builder_a = IndexBuilder(tmp_path / "a")
    builder_b = IndexBuilder(tmp_path / "b")
    chunks = _sample_batch()
    builder_a.build(chunks)
    builder_b.build(list(reversed(chunks)))

    _, meta_a = IndexBuilder.load(tmp_path / "a")
    _, meta_b = IndexBuilder.load(tmp_path / "b")
    assert [m.chunk_id for m in meta_a] == [m.chunk_id for m in meta_b]
    # And specifically, sorted by chunk.id ascending:
    assert [m.chunk_id for m in meta_a] == sorted(c.chunk.id for c in chunks)


# 10. Empty list builds an empty index gracefully.
def test_empty_input_builds_empty_index(tmp_path: Path) -> None:
    builder = IndexBuilder(tmp_path)
    result = builder.build([])
    assert result.total_chunks == 0
    assert builder.exists()
    index, metadata = IndexBuilder.load(tmp_path)
    assert index.ntotal == 0
    assert metadata == []


# 11. Atomic write: tmp pattern used and cleaned up.
def test_atomic_write_no_tmp_leftover(tmp_path: Path) -> None:
    IndexBuilder(tmp_path).build(_sample_batch())
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == [], f"unexpected .tmp leftovers: {leftovers}"

    # Sanity: metadata.json is valid JSON written via the atomic helper.
    payload = json.loads((tmp_path / METADATA_FILENAME).read_text("utf-8"))
    assert payload["model_name"] == _MODEL
    assert payload["embedding_dim"] == _DIM
    assert len(payload["chunks"]) == 3


# Bonus contract checks (not counted in the 11 required, but cheap and useful).


def test_search_returns_correct_chunk(tmp_path: Path) -> None:
    """End-to-end retriever pattern: search on the built index returns the matching metadata."""
    chunks = _sample_batch()
    IndexBuilder(tmp_path).build(chunks)
    index, metadata = IndexBuilder.load(tmp_path)

    target = sorted(chunks, key=lambda c: c.chunk.id)[0]
    query = np.asarray([target.embedding], dtype="float32")
    distances, indices = index.search(query, k=1)
    hit = metadata[int(indices[0][0])]
    assert hit.chunk_id == target.chunk.id
    assert distances[0][0] == pytest.approx(0.0, abs=1e-5)


def test_load_missing_index_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        IndexBuilder.load(tmp_path / "nope")


def test_inconsistent_dim_raises(tmp_path: Path) -> None:
    bad = [
        _make_embedded("a", vector=[0.0] * _DIM),
        EmbeddedChunk(
            chunk_id="b",
            embedding=[0.0] * (_DIM + 1),
            model_name=_MODEL,
            embedding_dim=_DIM + 1,
            chunk=_make_chunk("b"),
        ),
    ]
    with pytest.raises(ValueError):
        IndexBuilder(tmp_path).build(bad)
