"""
Embedder Module (P0-05).

Purpose: Encode CodeChunk objects into dense vector embeddings using
sentence-transformers. The model is loaded lazily so importing this
module is cheap; the heavy weights are pulled in only on first encode.

Contract:
    Input:  list[CodeChunk]   (from chunker, content already formatted)
    Output: list[EmbeddedChunk]  (preserves chunk_id, adds vector + model meta)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from src.local_agent.ingestion.chunker import CodeChunk

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 32


@dataclass(frozen=True)
class EmbeddedChunk:
    """A CodeChunk paired with its dense embedding."""

    chunk_id: str
    embedding: list[float]
    model_name: str
    embedding_dim: int
    chunk: CodeChunk


def to_embed_text(chunk: CodeChunk) -> str:
    """Return the text used for embedding. Uses chunk.content as-is — no reconstruction."""
    return chunk.content


class Embedder:
    """Sentence-transformer embedder with lazy model loading."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> SentenceTransformer:
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise ImportError(
                "sentence-transformers is required for embedding. "
                "Install it via `pip install sentence-transformers`."
            ) from error

        model = SentenceTransformer(self.model_name)
        # Determinism: eval mode disables dropout / training-time randomness.
        model.eval()
        self._model = model
        return model

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of the loaded model's output vectors."""
        model = self._load_model()
        dim = model.get_sentence_embedding_dimension()
        if dim is None:
            raise RuntimeError(f"Model {self.model_name} did not report embedding dimension")
        return int(dim)

    def encode_text(self, texts: list[str]) -> list[list[float]]:
        """Encode raw text strings (e.g. user queries) to embedding vectors."""
        if not texts:
            return []
        model = self._load_model()
        vectors = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        return [[float(v) for v in vectors[i]] for i in range(len(texts))]

    def embed(self, chunks: Iterable[CodeChunk]) -> list[EmbeddedChunk]:
        """Encode chunks to embeddings, preserving input order."""
        chunk_list = list(chunks)
        if not chunk_list:
            return []

        model = self._load_model()
        texts = [to_embed_text(chunk) for chunk in chunk_list]

        vectors = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=False,
        )

        dim = int(vectors.shape[1])
        return [
            EmbeddedChunk(
                chunk_id=chunk.id,
                embedding=[float(value) for value in vectors[index]],
                model_name=self.model_name,
                embedding_dim=dim,
                chunk=chunk,
            )
            for index, chunk in enumerate(chunk_list)
        ]


def embed_chunks(
    chunks: Iterable[CodeChunk],
    model_name: str = DEFAULT_MODEL_NAME,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[EmbeddedChunk]:
    """Functional API: embed chunks with a one-shot Embedder."""
    return Embedder(model_name=model_name, batch_size=batch_size).embed(chunks)


__all__ = [
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_MODEL_NAME",
    "EmbeddedChunk",
    "Embedder",
    "embed_chunks",
    "to_embed_text",
]
