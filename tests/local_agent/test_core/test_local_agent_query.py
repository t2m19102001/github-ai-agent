"""P0-09 LocalAgent.query() end-to-end tests using fake retriever / LLM."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pytest

from src.local_agent.core import (
    AgentResponse,
    LocalAgent,
    QueryConfig,
)
from src.local_agent.retrieval.context_builder import ContextBuilder
from src.local_agent.retrieval.retriever import RetrievalResult, RetrievalSource


def _make_result(rank: int, *, chunk_id: str | None = None) -> RetrievalResult:
    cid = chunk_id or f"c{rank}"
    return RetrievalResult(
        chunk_id=cid,
        file_path=f"/repo/{cid}.py",
        relative_path=f"{cid}.py",
        name=cid,
        qualified_name=cid,
        level="function",
        start_line=1,
        end_line=10,
        content=f"def {cid}(): pass",
        docstring=f"doc {cid}",
        symbols=[cid],
        parent_name=None,
        score=0.1 * rank,
        rank=rank,
        source=RetrievalSource.DENSE,
    )


@dataclass
class FakeRetriever:
    """Stand-in for BasicRetriever; records call args."""

    results: list[RetrievalResult] = field(default_factory=list)
    calls: list[tuple[str, int]] = field(default_factory=list)

    def retrieve(self, query: str, k: int = 10) -> list[RetrievalResult]:
        self.calls.append((query, k))
        return list(self.results)


@dataclass
class TrackingContextBuilder:
    """Wraps real ContextBuilder to count invocations."""

    inner: ContextBuilder
    calls: int = 0

    def build(self, query, retrieval_results, max_tokens=None):
        self.calls += 1
        return self.inner.build(query, retrieval_results, max_tokens=max_tokens)


@dataclass
class FakeLLM:
    """Deterministic fake LLM; can also raise on demand."""

    model_name: str = "fake-llm"
    response: str = "Overview:\n- ok\n\nKey points:\n- ok"
    calls: list[tuple[str, str, int, float]] = field(default_factory=list)
    raises: Exception | None = None
    handler: Callable[[str, str], str] | None = None

    def generate(self, system_prompt, user_prompt, max_tokens=1200, temperature=0.0):
        self.calls.append((system_prompt, user_prompt, max_tokens, temperature))
        if self.raises is not None:
            raise self.raises
        if self.handler is not None:
            return self.handler(system_prompt, user_prompt)
        return self.response


def _build_agent(
    *,
    retriever_results: list[RetrievalResult] | None = None,
    llm: FakeLLM | None = None,
    config: QueryConfig | None = None,
) -> tuple[LocalAgent, FakeRetriever, TrackingContextBuilder, FakeLLM]:
    retriever = FakeRetriever(results=retriever_results if retriever_results is not None else [_make_result(1), _make_result(2)])
    cb = TrackingContextBuilder(inner=ContextBuilder(max_tokens=1000, reserve_tokens=100))
    fake_llm = llm or FakeLLM()
    agent = LocalAgent(
        retriever=retriever,
        context_builder=cb,
        llm_client=fake_llm,
        config=config,
    )
    return agent, retriever, cb, fake_llm


# 1. Happy path: query returns AgentResponse.
def test_query_succeeds_with_valid_question() -> None:
    agent, _, _, _ = _build_agent()
    response = agent.query("how does this code work?")
    assert isinstance(response, AgentResponse)


# 2. Empty / whitespace question raises ValueError.
@pytest.mark.parametrize("bad_question", ["", "   ", "\n\t"])
def test_empty_question_raises(bad_question: str) -> None:
    agent, _, _, _ = _build_agent()
    with pytest.raises(ValueError):
        agent.query(bad_question)


# 3. Retriever called exactly once.
def test_retriever_called_once() -> None:
    agent, retriever, _, _ = _build_agent()
    agent.query("question")
    assert len(retriever.calls) == 1
    assert retriever.calls[0][0] == "question"
    assert retriever.calls[0][1] == agent.config.top_k


# 4. ContextBuilder called exactly once on happy path.
def test_context_builder_called_once() -> None:
    agent, _, cb, _ = _build_agent()
    agent.query("question")
    assert cb.calls == 1


# 5. LLM client called exactly once.
def test_llm_called_once() -> None:
    agent, _, _, llm = _build_agent()
    agent.query("question")
    assert len(llm.calls) == 1


# 6. AgentResponse.question preserves input.
def test_response_preserves_question() -> None:
    agent, _, _, _ = _build_agent()
    response = agent.query("what does foo do?")
    assert response.question == "what does foo do?"


# 7. retrieved_chunks is the list of chunk IDs.
def test_retrieved_chunks_lists_chunk_ids() -> None:
    agent, _, _, _ = _build_agent(
        retriever_results=[_make_result(1, chunk_id="alpha"), _make_result(2, chunk_id="beta")]
    )
    response = agent.query("question")
    assert response.retrieved_chunks == ["alpha", "beta"]


# 8. total_retrieved counts retriever output (pre-budget cut).
def test_total_retrieved_counts_pre_budget() -> None:
    results = [_make_result(i) for i in range(1, 6)]
    config = QueryConfig(top_k=5, max_context_tokens=200, reserve_tokens=100)
    agent, _, _, _ = _build_agent(retriever_results=results, config=config)
    response = agent.query("q")
    assert response.total_retrieved == 5


# 9. total_context_tokens comes from ContextWindow.
def test_total_context_tokens_from_window() -> None:
    agent, _, _, _ = _build_agent()
    response = agent.query("q")
    # Each chunk is "def cN(): pass" ~ 14 chars => max(1, 14//4) = 3 tokens. 2 chunks => 6.
    assert response.total_context_tokens == 6


# 10. Empty retriever results → safe fallback, no crash, no LLM call.
def test_empty_retrieval_returns_safe_fallback() -> None:
    agent, _, cb, llm = _build_agent(retriever_results=[])
    response = agent.query("question")
    assert response.total_retrieved == 0
    assert response.retrieved_chunks == []
    assert response.confidence == 0.0
    assert "not have enough information" in response.answer.lower()
    assert any("no results" in w.lower() for w in response.warnings)
    assert cb.calls == 0  # never invoked context builder
    assert llm.calls == []  # never invoked LLM


# 11. LLM exception → safe fallback + warning, no crash.
def test_llm_failure_returns_safe_fallback() -> None:
    failing_llm = FakeLLM(raises=RuntimeError("ollama timeout"))
    agent, _, _, _ = _build_agent(llm=failing_llm)
    response = agent.query("question")
    assert response.confidence == 0.0
    assert "llm call failed" in response.answer.lower()
    assert any("llm_error" in w for w in response.warnings)
    assert any("RuntimeError" in w for w in response.warnings)


# 12. User prompt contains question + formatted context.
def test_prompt_contains_question_and_context() -> None:
    agent, _, _, llm = _build_agent()
    agent.query("how does login work?")
    system, user, _, _ = llm.calls[0]
    assert "how does login work?" in user
    assert "Repository Context:" in user
    assert "Query: how does login work?" in user  # format from ContextBuilder
    assert "code analysis assistant" in system.lower()
    assert "do not have enough information" in system.lower()


# 13. Confidence in [0.0, 1.0].
def test_confidence_within_unit_range() -> None:
    agent, _, _, _ = _build_agent()
    response = agent.query("q")
    assert 0.0 <= response.confidence <= 1.0


# 14. Latency is positive.
def test_latency_ms_positive() -> None:
    agent, _, _, _ = _build_agent()
    response = agent.query("q")
    assert response.latency_ms > 0


# 15. Deterministic answer with deterministic fake LLM.
def test_deterministic_answer_with_deterministic_llm() -> None:
    agent, _, _, _ = _build_agent()
    a = agent.query("the same question")
    b = agent.query("the same question")
    assert a.answer == b.answer
    assert a.retrieved_chunks == b.retrieved_chunks
    assert a.total_context_tokens == b.total_context_tokens


# 16. With empty retrieval, agent must NOT invent — answer says insufficient info.
def test_no_invention_when_context_missing() -> None:
    agent, _, _, llm = _build_agent(retriever_results=[])
    response = agent.query("describe nonexistent_function")
    # No LLM call → no chance of hallucination.
    assert llm.calls == []
    assert "not have enough" in response.answer.lower()


# 17. AgentResponse.model_name comes from the LLM client attribute.
def test_model_name_propagates_from_llm_client() -> None:
    agent, _, _, _ = _build_agent(llm=FakeLLM(model_name="custom-model-7b"))
    response = agent.query("q")
    assert response.model_name == "custom-model-7b"


# 18. End-to-end happy path with all fakes wired.
def test_end_to_end_happy_path() -> None:
    results = [_make_result(1, chunk_id="alpha"), _make_result(2, chunk_id="beta")]
    llm = FakeLLM(
        model_name="happy-llm",
        handler=lambda system, user: f"answer:{user.split(chr(10))[0]}",
    )
    agent, retriever, cb, _ = _build_agent(retriever_results=results, llm=llm)

    response = agent.query("how does the system work?")

    assert response.question == "how does the system work?"
    assert response.retrieved_chunks == ["alpha", "beta"]
    assert response.total_retrieved == 2
    assert response.model_name == "happy-llm"
    assert response.confidence > 0
    assert response.latency_ms > 0
    assert len(retriever.calls) == 1
    assert cb.calls == 1
    assert response.answer.startswith("answer:Question:")


# Bonus: top_k respected when forwarding to retriever.
def test_top_k_forwarded_to_retriever() -> None:
    config = QueryConfig(top_k=3)
    agent, retriever, _, _ = _build_agent(config=config)
    agent.query("q")
    assert retriever.calls[0][1] == 3


# Bonus: warnings list defaults to empty on happy path.
def test_warnings_empty_on_happy_path() -> None:
    agent, _, _, _ = _build_agent()
    response = agent.query("q")
    assert response.warnings == []
