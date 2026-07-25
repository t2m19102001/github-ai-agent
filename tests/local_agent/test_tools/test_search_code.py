"""Tests for the search_code tool and its wiring into the registry."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

faiss = pytest.importorskip("faiss", reason="faiss-cpu required")
np = pytest.importorskip("numpy", reason="numpy required")

from src.local_agent.agent_loop import build_default_registry
from src.local_agent.indexing.index_builder import IndexBuilder
from src.local_agent.ingestion.chunker import ChunkLevel, CodeChunk
from src.local_agent.ingestion.embedder import EmbeddedChunk, Embedder
from src.local_agent.tools.search_code import SearchCodeTool

_DIM = 4
_MODEL = "fake-model"


class _FakeModel:
    def get_sentence_embedding_dimension(self) -> int:
        return _DIM

    def eval(self) -> None:
        return None

    def encode(self, texts, batch_size: int, **_):
        rows = [
            [hashlib.sha256(t.encode()).digest()[i] / 255.0 for i in range(_DIM)]
            for t in texts
        ]
        return np.asarray(rows, dtype="float32")


@pytest.fixture(autouse=True)
def _patch_embedder(monkeypatch):
    fake = _FakeModel()
    monkeypatch.setattr(
        Embedder,
        "_load_model",
        lambda self: setattr(self, "_model", fake) or fake,
    )


def _embed(text: str) -> list[float]:
    return [hashlib.sha256(text.encode()).digest()[i] / 255.0 for i in range(_DIM)]


def _index(tmp_path: Path, items: list[tuple[str, str]]) -> Path:
    chunks = []
    for cid, content in items:
        chunk = CodeChunk(
            id=cid, level=ChunkLevel.FUNCTION, file_path=f"/repo/{cid}.py",
            relative_path=f"{cid}.py", name=cid, qualified_name=cid,
            start_line=1, end_line=5, content=content, docstring=None,
            imports=[], symbols=[cid], parent_name=None, metadata={},
            token_count=None,
        )
        chunks.append(
            EmbeddedChunk(
                chunk_id=cid, embedding=_embed(content), model_name=_MODEL,
                embedding_dim=_DIM, chunk=chunk,
            )
        )
    index_dir = tmp_path / "index"
    IndexBuilder(index_dir).build(chunks)
    return index_dir


def test_search_code_returns_hits(tmp_path: Path) -> None:
    index_dir = _index(
        tmp_path,
        [("a", "retry logic with backoff"), ("b", "unrelated helper")],
    )
    tool = SearchCodeTool(index_dir=index_dir, model_name=_MODEL)
    result = tool.run({"query": "retry logic"})
    assert result.ok
    assert "a.py" in result.content


def test_search_code_requires_query(tmp_path: Path) -> None:
    index_dir = _index(tmp_path, [("a", "x")])
    assert not SearchCodeTool(index_dir, _MODEL).run({}).ok


def test_search_code_missing_index_is_failure(tmp_path: Path) -> None:
    tool = SearchCodeTool(index_dir=tmp_path / "nope", model_name=_MODEL)
    result = tool.run({"query": "anything"})
    assert not result.ok
    assert "no code index" in result.content


def test_registry_includes_search_code_when_index_given(tmp_path: Path) -> None:
    index_dir = _index(tmp_path, [("a", "content")])
    reg = build_default_registry(
        tmp_path, index_dir=index_dir, embed_model=_MODEL
    )
    assert "search_code" in reg.names()


def test_registry_omits_search_code_without_index(tmp_path: Path) -> None:
    reg = build_default_registry(tmp_path)
    assert "search_code" not in reg.names()
    # The read-only file/git tools are always present.
    assert "read_file" in reg.names()
