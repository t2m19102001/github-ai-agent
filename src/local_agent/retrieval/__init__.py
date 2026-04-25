"""
Retrieval Module.

Purpose: Retrieve relevant code chunks for queries.
Input: Query string
Output: Ranked list of chunks with relevance scores

Components:
    retriever: Hybrid search (dense + sparse)
    ranker: Result ranking (RRF)
    context_builder: Context assembly for LLM
"""

from src.local_agent.retrieval.retriever import (
    BasicRetriever,
    RetrievalResult,
    RetrievalSource,
)
from src.local_agent.retrieval.ranker import Ranker
from src.local_agent.retrieval.context_builder import (
    ContextBuilder,
    ContextMetadata,
    ContextWindow,
)

__all__ = [
    "BasicRetriever",
    "RetrievalResult",
    "RetrievalSource",
    "Ranker",
    "ContextBuilder",
    "ContextMetadata",
    "ContextWindow",
]
