"""End-to-end ingestion pipeline tests: crawler → parser → symbols → chunker → embedder."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.local_agent.ingestion import (
    ChunkLevel,
    Embedder,
    chunk_files,
    crawl_python_files,
    embed_chunks,
    extract_symbols_batch,
    parse_files,
)


_FAKE_DIM = 8


class _FakeModel:
    def get_sentence_embedding_dimension(self) -> int:
        return _FAKE_DIM

    def eval(self) -> None:
        return None

    def encode(self, texts, batch_size: int, **_):
        import numpy as np

        rows = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            rows.append([digest[i] / 255.0 for i in range(_FAKE_DIM)])
        return np.asarray(rows, dtype="float32")


def test_full_pipeline_runs(monkeypatch, repo_root: Path) -> None:
    pytest.importorskip("numpy")
    fake = _FakeModel()
    monkeypatch.setattr(
        Embedder, "_load_model", lambda self: setattr(self, "_model", fake) or fake
    )

    crawl = crawl_python_files(repo_root)
    paths = [Path(record["path"]) for record in crawl["files"]]
    assert paths, "crawler returned no files"

    parsed = parse_files(paths, repo_root=repo_root)
    assert any(pf.parse_success for pf in parsed)

    symbols = extract_symbols_batch(parsed)
    symbols_map = {s.file_path: s for s in symbols}

    chunks = chunk_files(parsed, symbols_map)
    assert chunks, "expected at least one chunk"
    assert any(c.level == ChunkLevel.FILE for c in chunks)

    embedded = embed_chunks(chunks, model_name="fake")
    assert len(embedded) == len(chunks)
    assert all(e.embedding_dim == _FAKE_DIM for e in embedded)


def test_pipeline_docstrings_survive_end_to_end(monkeypatch, repo_root: Path) -> None:
    """Regression: the docstring contract bug must stay fixed in the full pipeline."""
    pytest.importorskip("numpy")
    fake = _FakeModel()
    monkeypatch.setattr(
        Embedder, "_load_model", lambda self: setattr(self, "_model", fake) or fake
    )

    crawl = crawl_python_files(repo_root)
    paths = [Path(record["path"]) for record in crawl["files"]]
    parsed = parse_files(paths, repo_root=repo_root)
    symbols = extract_symbols_batch(parsed)
    chunks = chunk_files(parsed, {s.file_path: s for s in symbols})

    greeter = next(c for c in chunks if c.level == ChunkLevel.CLASS and c.name == "Greeter")
    assert greeter.docstring == "Greeter class docstring."

    greet = next(c for c in chunks if c.level == ChunkLevel.METHOD and c.name == "greet")
    assert greet.docstring == "Greet method docstring."


def test_pipeline_is_deterministic(monkeypatch, repo_root: Path) -> None:
    pytest.importorskip("numpy")
    fake = _FakeModel()
    monkeypatch.setattr(
        Embedder, "_load_model", lambda self: setattr(self, "_model", fake) or fake
    )

    def run() -> list[str]:
        crawl = crawl_python_files(repo_root)
        paths = [Path(record["path"]) for record in crawl["files"]]
        parsed = parse_files(paths, repo_root=repo_root)
        symbols = extract_symbols_batch(parsed)
        chunks = chunk_files(parsed, {s.file_path: s for s in symbols})
        embedded = embed_chunks(chunks, model_name="fake")
        return [e.chunk_id for e in embedded]

    assert run() == run()
