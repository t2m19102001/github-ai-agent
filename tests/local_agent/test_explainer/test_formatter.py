"""MarkdownFormatter tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.local_agent.core import AgentResponse
from src.local_agent.explainer.citation import Citation
from src.local_agent.explainer.formatter import MarkdownFormatter, format_report


def _make_response(
    *,
    question: str = "What does login do?",
    answer: str = "Validates credentials and issues a session token.",
    retrieved_chunks: list[str] | None = None,
    total_retrieved: int = 2,
    total_context_tokens: int = 12,
    confidence: float = 0.75,
    warnings: list[str] | None = None,
) -> AgentResponse:
    return AgentResponse(
        question=question,
        answer=answer,
        retrieved_chunks=retrieved_chunks if retrieved_chunks is not None else ["c1", "c2"],
        total_retrieved=total_retrieved,
        total_context_tokens=total_context_tokens,
        confidence=confidence,
        model_name="fake-model",
        latency_ms=42,
        timestamp=datetime(2026, 4, 25, 10, tzinfo=timezone.utc),
        warnings=warnings if warnings is not None else [],
    )


def _make_citation(rank: int = 1, **overrides) -> Citation:
    base = dict(
        chunk_id=f"c{rank}",
        relative_path="src/auth.py",
        file_path="/repo/src/auth.py",
        name="login",
        qualified_name="AuthService.login",
        level="method",
        start_line=42,
        end_line=88,
        score=0.123,
        rank=rank,
    )
    base.update(overrides)
    return Citation(**base)


def test_format_report_contains_question_section() -> None:
    md = MarkdownFormatter().format_report(_make_response(), [_make_citation()])
    assert "## Question" in md
    assert "What does login do?" in md


def test_format_report_contains_answer_section() -> None:
    md = MarkdownFormatter().format_report(_make_response(), [_make_citation()])
    assert "## Answer" in md
    assert "Validates credentials" in md


def test_format_report_renders_each_citation_as_markdown() -> None:
    citations = [_make_citation(rank=1), _make_citation(rank=2, chunk_id="c2")]
    md = MarkdownFormatter().format_report(_make_response(), citations)
    assert "## Citations" in md
    # Both citations rendered as markdown links
    assert "AuthService.login" in md
    assert "src/auth.py#L42-L88" in md
    assert "rank 1" in md
    assert "rank 2" in md
    assert "score 0.1230" in md


def test_format_report_no_citations_section_says_no_chunks() -> None:
    md = MarkdownFormatter().format_report(_make_response(), [])
    assert "## Citations" in md
    assert "no source chunks" in md.lower()


def test_format_report_metadata_section() -> None:
    response = _make_response(confidence=0.83, total_context_tokens=2048)
    md = MarkdownFormatter().format_report(response, [_make_citation()])
    assert "## Metadata" in md
    assert "Confidence: **0.83**" in md
    assert "fake-model" in md
    assert "Latency: 42 ms" in md
    assert "Context tokens: 2048" in md


def test_format_report_lists_warnings_when_present() -> None:
    response = _make_response(warnings=["llm_error:RuntimeError:timeout", "no results"])
    md = MarkdownFormatter().format_report(response, [_make_citation()])
    assert "Warnings:" in md
    assert "llm_error:RuntimeError:timeout" in md
    assert "no results" in md


def test_format_report_no_warnings_block_when_clean() -> None:
    md = MarkdownFormatter().format_report(_make_response(), [_make_citation()])
    assert "Warnings:" not in md


def test_format_report_handles_empty_answer() -> None:
    response = _make_response(answer="")
    md = MarkdownFormatter().format_report(response, [])
    assert "no answer produced" in md.lower()


def test_format_report_deterministic_for_same_input() -> None:
    response = _make_response()
    citations = [_make_citation(rank=1), _make_citation(rank=2, chunk_id="c2")]
    a = MarkdownFormatter().format_report(response, citations)
    b = MarkdownFormatter().format_report(response, citations)
    assert a == b


def test_functional_api_matches_class() -> None:
    response = _make_response()
    citations = [_make_citation()]
    assert format_report(response, citations) == MarkdownFormatter().format_report(response, citations)


def test_format_report_ends_with_newline() -> None:
    md = MarkdownFormatter().format_report(_make_response(), [_make_citation()])
    assert md.endswith("\n")
