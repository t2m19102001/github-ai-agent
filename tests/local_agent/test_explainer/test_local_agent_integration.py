"""Integration: LocalAgent.query() must populate AgentResponse.citations."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from src.local_agent.core import LocalAgent, QueryConfig
from src.local_agent.explainer.citation import Citation
from src.local_agent.explainer.formatter import format_report
from src.local_agent.retrieval.context_builder import ContextBuilder
from src.local_agent.retrieval.retriever import RetrievalResult, RetrievalSource


def _make_result(rank: int, *, chunk_id: str | None = None) -> RetrievalResult:
    cid = chunk_id or f"c{rank}"
    return RetrievalResult(
        chunk_id=cid,
        file_path=f"/repo/{cid}.py",
        relative_path=f"{cid}.py",
        name=cid,
        qualified_name=f"Mod.{cid}",
        level="function",
        start_line=10 * rank,
        end_line=10 * rank + 5,
        content=f"def {cid}(): pass",
        docstring=None,
        symbols=[cid],
        parent_name=None,
        score=0.1 * rank,
        rank=rank,
        source=RetrievalSource.DENSE,
    )


@dataclass
class FakeRetriever:
    results: list[RetrievalResult]

    def retrieve(self, query, k=10):
        return list(self.results)


@dataclass
class FakeLLM:
    model_name: str = "fake-llm"
    response: str = "Some answer"
    raises: Exception | None = None
    calls: list[tuple] = field(default_factory=list)

    def generate(self, system_prompt, user_prompt, max_tokens=1200, temperature=0.0):
        self.calls.append((system_prompt, user_prompt))
        if self.raises is not None:
            raise self.raises
        return self.response


def _agent(results: list[RetrievalResult], llm: FakeLLM | None = None) -> LocalAgent:
    return LocalAgent(
        retriever=FakeRetriever(results=results),
        context_builder=ContextBuilder(max_tokens=2000, reserve_tokens=100),
        llm_client=llm or FakeLLM(),
        config=QueryConfig(top_k=8),
    )


def test_query_populates_citations_on_happy_path() -> None:
    results = [_make_result(1, chunk_id="alpha"), _make_result(2, chunk_id="beta")]
    response = _agent(results).query("how does it work?")
    assert len(response.citations) == 2
    assert all(isinstance(c, Citation) for c in response.citations)
    assert {c.chunk_id for c in response.citations} == {"alpha", "beta"}


def test_citations_match_retrieved_chunks_ordering() -> None:
    results = [_make_result(1, chunk_id="a"), _make_result(2, chunk_id="b")]
    response = _agent(results).query("q")
    assert [c.chunk_id for c in response.citations] == response.retrieved_chunks


def test_citations_empty_when_retrieval_empty() -> None:
    response = _agent(results=[]).query("q")
    assert response.citations == []
    assert response.retrieved_chunks == []


def test_citations_preserved_on_llm_failure() -> None:
    results = [_make_result(1, chunk_id="alpha")]
    llm = FakeLLM(raises=RuntimeError("ollama down"))
    response = _agent(results, llm=llm).query("q")
    # LLM failed but we still retrieved → citations available for the user
    assert len(response.citations) == 1
    assert response.citations[0].chunk_id == "alpha"


def test_citation_qualified_name_carried_through() -> None:
    results = [_make_result(1, chunk_id="login")]
    response = _agent(results).query("q")
    assert response.citations[0].qualified_name == "Mod.login"


def test_format_report_works_on_real_response() -> None:
    """End-to-end: query → format_report produces usable markdown."""
    results = [_make_result(1, chunk_id="alpha"), _make_result(2, chunk_id="beta")]
    response = _agent(results).query("how does X work?")
    md = format_report(response, response.citations)
    assert "## Question" in md
    assert "how does X work?" in md
    assert "## Answer" in md
    assert "## Citations" in md
    # Both chunks rendered as markdown links
    assert "alpha.py#L10-L15" in md
    assert "beta.py#L20-L25" in md
