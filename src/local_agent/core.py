"""
LocalAgent (P0-09).

End-to-end query handler that orchestrates the RAG flow:

    question
        → retriever (P0-07)
            → context_builder (P0-08)
                → local LLM (injected)
                    → AgentResponse

The agent never invents file/function names: the prompt is grounded on the
retrieved context only. When retrieval is empty or the LLM fails, the agent
returns a safe fallback response with explicit warnings instead of crashing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from src.local_agent.retrieval.context_builder import ContextBuilder, ContextWindow
from src.local_agent.retrieval.retriever import BasicRetriever, RetrievalResult


_NO_RESULTS_ANSWER = (
    "I do not have enough information from the indexed repository "
    "to answer this question."
)
_LLM_FAILURE_ANSWER = (
    "I could not generate an answer because the local LLM call failed. "
    "Please retry or check that the LLM service is available."
)
_SYSTEM_PROMPT = (
    "You are a code analysis assistant.\n"
    "Answer only using the provided repository context.\n"
    "If the answer is not supported by the context, say you do not have "
    "enough information.\n"
    "Be precise and avoid guessing. Do not invent file or function names "
    "that are not present in the context."
)
_USER_PROMPT_TEMPLATE = (
    "Question: {question}\n\n"
    "Repository Context:\n{context}\n\n"
    "Answer in this format:\n"
    "Overview:\n- ...\n\n"
    "Key points:\n- ..."
)


class LLMClientProtocol(Protocol):
    """Structural type for any local LLM client the agent can drive."""

    model_name: str

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1200,
        temperature: float = 0.0,
    ) -> str: ...


@dataclass(frozen=True)
class QueryConfig:
    """Knobs for a single query run."""

    top_k: int = 8
    max_context_tokens: int = 32000
    reserve_tokens: int = 4000
    max_answer_tokens: int = 1200
    temperature: float = 0.0


@dataclass(frozen=True)
class AgentResponse:
    """Structured answer + provenance metadata."""

    question: str
    answer: str
    retrieved_chunks: list[str]
    total_retrieved: int
    total_context_tokens: int
    confidence: float
    model_name: str
    latency_ms: int
    timestamp: datetime
    warnings: list[str] = field(default_factory=list)


class LocalAgent:
    """Coordinates retriever → context builder → LLM into a single query call."""

    def __init__(
        self,
        retriever: BasicRetriever,
        context_builder: ContextBuilder,
        llm_client: LLMClientProtocol,
        config: QueryConfig | None = None,
    ) -> None:
        self.retriever = retriever
        self.context_builder = context_builder
        self.llm_client = llm_client
        self.config = config or QueryConfig()

    def query(self, question: str) -> AgentResponse:
        """Run the full RAG pipeline and return a structured AgentResponse."""
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty, non-whitespace string")

        started = time.perf_counter()
        warnings: list[str] = []

        retrieved: list[RetrievalResult] = self.retriever.retrieve(
            question, k=self.config.top_k
        )
        total_retrieved = len(retrieved)

        if not retrieved:
            warnings.append("retriever returned no results")
            return self._build_response(
                question=question,
                answer=_NO_RESULTS_ANSWER,
                retrieved_chunks=[],
                total_retrieved=0,
                total_context_tokens=0,
                confidence=0.0,
                started=started,
                warnings=warnings,
            )

        context_window: ContextWindow = self.context_builder.build(
            query=question,
            retrieval_results=retrieved,
            max_tokens=self.config.max_context_tokens,
        )

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            question=question,
            context=context_window.to_prompt_fragment(),
        )

        try:
            answer = self.llm_client.generate(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=self.config.max_answer_tokens,
                temperature=self.config.temperature,
            )
        except Exception as error:
            warnings.append(f"llm_error:{type(error).__name__}:{error}")
            return self._build_response(
                question=question,
                answer=_LLM_FAILURE_ANSWER,
                retrieved_chunks=[c.chunk_id for c in context_window.chunks],
                total_retrieved=total_retrieved,
                total_context_tokens=context_window.total_tokens,
                confidence=0.0,
                started=started,
                warnings=warnings,
            )

        confidence = _heuristic_confidence(
            retrieved_count=len(context_window.chunks),
            top_k=self.config.top_k,
        )

        return self._build_response(
            question=question,
            answer=answer.strip() if isinstance(answer, str) else str(answer),
            retrieved_chunks=[c.chunk_id for c in context_window.chunks],
            total_retrieved=total_retrieved,
            total_context_tokens=context_window.total_tokens,
            confidence=confidence,
            started=started,
            warnings=warnings,
        )

    def _build_response(
        self,
        *,
        question: str,
        answer: str,
        retrieved_chunks: list[str],
        total_retrieved: int,
        total_context_tokens: int,
        confidence: float,
        started: float,
        warnings: list[str],
    ) -> AgentResponse:
        latency_ms = max(1, int((time.perf_counter() - started) * 1000))
        return AgentResponse(
            question=question,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            total_retrieved=total_retrieved,
            total_context_tokens=total_context_tokens,
            confidence=confidence,
            model_name=getattr(self.llm_client, "model_name", "unknown"),
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc),
            warnings=list(warnings),
        )


def _heuristic_confidence(retrieved_count: int, top_k: int) -> float:
    """V1 confidence: fraction of top-k slots that returned a chunk, clipped to [0,1]."""
    if retrieved_count <= 0 or top_k <= 0:
        return 0.0
    return min(1.0, retrieved_count / top_k)


__all__ = [
    "AgentResponse",
    "LLMClientProtocol",
    "LocalAgent",
    "QueryConfig",
]
