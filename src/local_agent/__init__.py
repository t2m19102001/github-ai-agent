"""
Local AI Agent System.

A read-only, suggest-only AI agent for codebase analysis, planning, and code generation.
Uses Ollama (Llama 3 8B) for local inference with FAISS vector storage and SQLite memory.

Architecture:
    Ingestion → Indexing → Retrieval → Planner → Explainer → (SWE-1.6 Executor)

Modules:
    ingestion: Code parsing and chunking (tree-sitter)
    indexing: Vector index building (FAISS)
    retrieval: Context retrieval (hybrid search)
    planner: Implementation planning
    explainer: Output formatting with citations
    memory: Session management (SQLite)
    tools: Read-only file operations
    guardrails: Safety validation
    integration: SWE-1.6 JSON contract
"""

from src.local_agent.config import LocalAgentConfig
from src.local_agent.core import (
    AgentResponse,
    LLMClientProtocol,
    LocalAgent,
    QueryConfig,
)

__all__ = [
    "LocalAgentConfig",
    "LocalAgent",
    "AgentResponse",
    "QueryConfig",
    "LLMClientProtocol",
]
