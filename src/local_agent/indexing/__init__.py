"""
Indexing Module.

Purpose: Build and manage vector indices for code chunks.
Input: Code chunks with embeddings
Output: FAISS index with metadata

Components:
    embedder: Embedding generation (sentence-transformers)
    index_builder: FAISS index creation
    metadata: Metadata storage (SQLite)
"""

from src.local_agent.indexing.embedder import EmbeddedChunk, Embedder, to_embed_text
from src.local_agent.indexing.index_builder import (
    INDEX_FILENAME,
    METADATA_FILENAME,
    IndexBuilder,
    IndexBuildResult,
    IndexMetadata,
)
from src.local_agent.indexing.metadata import MetadataStore

__all__ = [
    "EmbeddedChunk",
    "Embedder",
    "to_embed_text",
    "IndexBuilder",
    "IndexBuildResult",
    "IndexMetadata",
    "INDEX_FILENAME",
    "METADATA_FILENAME",
    "MetadataStore",
]
