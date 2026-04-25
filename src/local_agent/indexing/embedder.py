"""
Embedder — backward-compatibility shim.

The canonical embedder lives at `src/local_agent/ingestion/embedder.py`.
This module re-exports the same symbols so legacy import paths keep working:

    from src.local_agent.indexing.embedder import Embedder, EmbeddedChunk

Prefer the canonical path in new code:

    from src.local_agent.ingestion.embedder import Embedder, EmbeddedChunk

This wrapper exists only because `src/local_agent/indexing/embedder.py` was
historically a duplicate implementation. It now contains zero business logic.
"""

from __future__ import annotations

from src.local_agent.ingestion.embedder import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MODEL_NAME,
    EmbeddedChunk,
    Embedder,
    embed_chunks,
    to_embed_text,
)

__all__ = [
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_MODEL_NAME",
    "EmbeddedChunk",
    "Embedder",
    "embed_chunks",
    "to_embed_text",
]
