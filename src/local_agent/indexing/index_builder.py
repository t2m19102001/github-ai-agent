"""
FAISS Index Builder (P0-06).

Build a searchable vector index from EmbeddedChunk objects produced by the
P0-05 embedder, persist it to disk alongside a JSON metadata sidecar, and
load it back for the downstream P0-07 retriever.

Storage layout:
    {index_dir}/
        code.index       (FAISS binary)
        metadata.json    {chunks: [...], model_name: str, embedding_dim: int}

Determinism contract:
    The FAISS integer ID order is `sorted(chunk.id)`. Callers MUST NOT assume
    insert-order matches the input list — the retriever maps FAISS row N to
    `metadata[N]`, both of which are sorted by chunk.id.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.local_agent.ingestion.embedder import EmbeddedChunk

if TYPE_CHECKING:
    import faiss


INDEX_FILENAME = "code.index"
METADATA_FILENAME = "metadata.json"


@dataclass(frozen=True)
class IndexMetadata:
    """Per-chunk record persisted alongside the FAISS index."""

    chunk_id: str
    file_path: str
    relative_path: str | None
    name: str | None
    qualified_name: str | None
    level: str
    start_line: int
    end_line: int
    docstring: str | None
    symbols: list[str]
    parent_name: str | None
    content: str
    model_name: str


@dataclass(frozen=True)
class IndexBuildResult:
    """Summary of a successful index build."""

    index_path: str
    metadata_path: str
    total_chunks: int
    embedding_dim: int
    model_name: str


class IndexBuilder:
    """Builds and loads FAISS IndexFlatL2 indices with JSON metadata sidecars."""

    def __init__(self, index_dir: str | Path) -> None:
        self.index_dir = Path(index_dir).expanduser()

    @property
    def index_path(self) -> Path:
        return self.index_dir / INDEX_FILENAME

    @property
    def metadata_path(self) -> Path:
        return self.index_dir / METADATA_FILENAME

    def exists(self) -> bool:
        """Return True iff both index file and metadata sidecar are present."""
        return self.index_path.is_file() and self.metadata_path.is_file()

    def build(self, embedded_chunks: list[EmbeddedChunk]) -> IndexBuildResult:
        """Build a fresh FAISS index from embedded chunks and persist to disk."""
        faiss = _import_faiss()
        self.index_dir.mkdir(parents=True, exist_ok=True)

        ordered = sorted(embedded_chunks, key=lambda item: item.chunk.id)
        embedding_dim, model_name = _resolve_dim_and_model(ordered)

        index = faiss.IndexFlatL2(embedding_dim)
        if ordered:
            import numpy as np

            matrix = np.asarray(
                [item.embedding for item in ordered],
                dtype="float32",
            )
            if matrix.shape != (len(ordered), embedding_dim):
                raise ValueError(
                    f"Embedding shape mismatch: got {matrix.shape}, "
                    f"expected ({len(ordered)}, {embedding_dim})"
                )
            index.add(matrix)

        metadata = [_to_metadata(item) for item in ordered]
        _atomic_write_index(faiss=faiss, index=index, target=self.index_path)
        _atomic_write_json(
            payload={
                "chunks": [asdict(item) for item in metadata],
                "model_name": model_name,
                "embedding_dim": embedding_dim,
            },
            target=self.metadata_path,
        )

        return IndexBuildResult(
            index_path=str(self.index_path),
            metadata_path=str(self.metadata_path),
            total_chunks=len(ordered),
            embedding_dim=embedding_dim,
            model_name=model_name,
        )

    @classmethod
    def load(cls, index_dir: str | Path) -> tuple[faiss.Index, list[IndexMetadata]]:
        """Load FAISS index + metadata list from disk; metadata[i] maps to FAISS ID i."""
        faiss = _import_faiss()
        builder = cls(index_dir)
        if not builder.exists():
            raise FileNotFoundError(
                f"Index not found at {builder.index_dir}. "
                f"Expected {INDEX_FILENAME} + {METADATA_FILENAME}."
            )

        index = faiss.read_index(str(builder.index_path))
        with builder.metadata_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        chunks = payload.get("chunks", [])
        metadata = [IndexMetadata(**record) for record in chunks]
        return index, metadata


def _import_faiss():
    try:
        import faiss
    except ImportError as error:
        raise ImportError(
            "faiss-cpu is required for IndexBuilder. "
            "Install via `pip install faiss-cpu`."
        ) from error
    return faiss


def _resolve_dim_and_model(ordered: list[EmbeddedChunk]) -> tuple[int, str]:
    if not ordered:
        # Empty input: fall back to documented default so the index is still loadable.
        return 384, ""

    first = ordered[0]
    embedding_dim = first.embedding_dim or len(first.embedding)
    if embedding_dim <= 0:
        raise ValueError("First embedding has non-positive dimension")

    model_name = first.model_name
    for item in ordered[1:]:
        if (item.embedding_dim or len(item.embedding)) != embedding_dim:
            raise ValueError(
                f"Inconsistent embedding dimensions in batch: "
                f"{embedding_dim} vs {item.embedding_dim or len(item.embedding)}"
            )
        if item.model_name != model_name:
            raise ValueError(
                f"Inconsistent model_name in batch: "
                f"{model_name!r} vs {item.model_name!r}"
            )
    return embedding_dim, model_name


def _to_metadata(item: EmbeddedChunk) -> IndexMetadata:
    chunk = item.chunk
    return IndexMetadata(
        chunk_id=chunk.id,
        file_path=chunk.file_path,
        relative_path=chunk.relative_path,
        name=chunk.name,
        qualified_name=chunk.qualified_name,
        level=chunk.level.value if hasattr(chunk.level, "value") else str(chunk.level),
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        docstring=chunk.docstring,
        symbols=list(chunk.symbols),
        parent_name=chunk.parent_name,
        content=chunk.content,
        model_name=item.model_name,
    )


def _atomic_write_json(payload: dict, target: Path) -> None:
    tmp = target.with_suffix(target.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)


def _atomic_write_index(faiss, index, target: Path) -> None:
    tmp = target.with_suffix(target.suffix + ".tmp")
    faiss.write_index(index, str(tmp))
    os.replace(tmp, target)


__all__ = [
    "INDEX_FILENAME",
    "METADATA_FILENAME",
    "IndexBuilder",
    "IndexBuildResult",
    "IndexMetadata",
]
