"""Citation linker + Citation dataclass tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.local_agent.core import AgentResponse
from src.local_agent.explainer.citation import Citation, CitationLinker, link_chunks
from src.local_agent.retrieval.retriever import RetrievalResult, RetrievalSource


_UNSET = object()


def _make_chunk(
    rank: int,
    *,
    chunk_id: str | None = None,
    relative_path=_UNSET,
    qualified_name: str | None = "Foo.bar",
    name: str | None = "bar",
    start_line: int = 10,
    end_line: int = 25,
    score: float = 0.42,
    level: str = "method",
) -> RetrievalResult:
    cid = chunk_id or f"c{rank}"
    rel = f"{cid}.py" if relative_path is _UNSET else relative_path
    return RetrievalResult(
        chunk_id=cid,
        file_path=f"/repo/{cid}.py",
        relative_path=rel,
        name=name,
        qualified_name=qualified_name,
        level=level,
        start_line=start_line,
        end_line=end_line,
        content=f"def {name}(): pass",
        docstring=None,
        symbols=[],
        parent_name=None,
        score=score,
        rank=rank,
        source=RetrievalSource.DENSE,
    )


def test_link_returns_one_citation_per_chunk() -> None:
    chunks = [_make_chunk(1), _make_chunk(2), _make_chunk(3)]
    citations = CitationLinker().link(chunks)
    assert len(citations) == 3
    assert all(isinstance(c, Citation) for c in citations)


def test_link_preserves_input_order() -> None:
    chunks = [_make_chunk(3), _make_chunk(1), _make_chunk(2)]
    citations = CitationLinker().link(chunks)
    assert [c.rank for c in citations] == [3, 1, 2]


def test_citation_fields_copied_from_chunk() -> None:
    chunk = _make_chunk(
        7,
        chunk_id="alpha",
        relative_path="src/foo.py",
        qualified_name="Foo.alpha",
        name="alpha",
        start_line=42,
        end_line=88,
        score=0.123,
        level="function",
    )
    [citation] = CitationLinker().link([chunk])
    assert citation.chunk_id == "alpha"
    assert citation.relative_path == "src/foo.py"
    assert citation.file_path == "/repo/alpha.py"
    assert citation.name == "alpha"
    assert citation.qualified_name == "Foo.alpha"
    assert citation.level == "function"
    assert citation.start_line == 42
    assert citation.end_line == 88
    assert citation.score == 0.123
    assert citation.rank == 7


def test_to_markdown_uses_qualified_name_as_label() -> None:
    chunk = _make_chunk(1, qualified_name="AuthService.login", relative_path="src/auth.py", start_line=42, end_line=88)
    [citation] = CitationLinker().link([chunk])
    md = citation.to_markdown()
    assert md == "[AuthService.login (src/auth.py:42-88)](src/auth.py#L42-L88)"


def test_to_markdown_falls_back_to_name_then_path() -> None:
    chunk = _make_chunk(1, qualified_name=None, name="bare", relative_path="x.py")
    [citation] = CitationLinker().link([chunk])
    assert citation.to_markdown().startswith("[bare (x.py:")


def test_to_markdown_escapes_brackets_in_label() -> None:
    # A label containing ] would otherwise terminate the link text early,
    # producing a broken markdown link.
    chunk = _make_chunk(
        1, qualified_name="Foo].bar[", name=None, relative_path="src/a.py",
        start_line=1, end_line=2,
    )
    [citation] = CitationLinker().link([chunk])
    md = citation.to_markdown()
    # Brackets in the label must be backslash-escaped so the link text stays intact.
    assert r"Foo\].bar\[" in md
    assert md == r"[Foo\].bar\[ (src/a.py:1-2)](src/a.py#L1-L2)"


def test_to_markdown_wraps_path_with_spaces_in_angle_brackets() -> None:
    # A destination with spaces/parens breaks a bare markdown URL; CommonMark
    # allows wrapping the destination in <...>.
    chunk = _make_chunk(
        1, qualified_name="fn", name=None, relative_path="a (copy).py",
        start_line=3, end_line=4,
    )
    [citation] = CitationLinker().link([chunk])
    md = citation.to_markdown()
    assert "(<a (copy).py#L3-L4>)" in md
    assert md == "[fn (a (copy).py:3-4)](<a (copy).py#L3-L4>)"


def test_to_markdown_plain_path_not_wrapped() -> None:
    # Regression guard: ordinary paths must NOT gain angle brackets.
    chunk = _make_chunk(
        1, qualified_name="AuthService.login", name=None, relative_path="src/auth.py",
        start_line=42, end_line=88,
    )
    [citation] = CitationLinker().link([chunk])
    assert citation.to_markdown() == (
        "[AuthService.login (src/auth.py:42-88)](src/auth.py#L42-L88)"
    )


def test_to_markdown_uses_path_as_label_when_unnamed() -> None:
    chunk = _make_chunk(1, qualified_name=None, name=None, relative_path="x.py")
    [citation] = CitationLinker().link([chunk])
    md = citation.to_markdown()
    assert md.startswith("[x.py (x.py:")


def test_display_path_falls_back_to_file_path_when_relative_missing() -> None:
    chunk = _make_chunk(1, relative_path=None)
    [citation] = CitationLinker().link([chunk])
    assert citation.relative_path is None
    assert citation.display_path() == citation.file_path
    assert "/repo/c1.py" in citation.to_markdown()


def test_to_text_returns_label_path_lines() -> None:
    chunk = _make_chunk(1, qualified_name="Foo.bar", relative_path="src/foo.py", start_line=10, end_line=15)
    [citation] = CitationLinker().link([chunk])
    assert citation.to_text() == "Foo.bar — src/foo.py:10-15"


def test_to_text_drops_label_when_no_name() -> None:
    chunk = _make_chunk(
        1,
        qualified_name=None,
        name=None,
        relative_path="x.py",
        start_line=1,
        end_line=10,
    )
    [citation] = CitationLinker().link([chunk])
    assert citation.to_text() == "x.py:1-10"


def test_link_chunks_functional_api_matches_class() -> None:
    chunks = [_make_chunk(1), _make_chunk(2)]
    a = CitationLinker().link(chunks)
    b = link_chunks(chunks)
    assert a == b


def test_empty_input_returns_empty_list() -> None:
    assert CitationLinker().link([]) == []
    assert link_chunks([]) == []


def test_citation_is_frozen() -> None:
    [citation] = CitationLinker().link([_make_chunk(1)])
    with pytest.raises(Exception):
        citation.chunk_id = "mutated"  # type: ignore[misc]


def test_agent_response_default_citations_empty() -> None:
    """AgentResponse has citations field with default empty list (backward compat)."""
    response = AgentResponse(
        question="q",
        answer="a",
        retrieved_chunks=[],
        total_retrieved=0,
        total_context_tokens=0,
        confidence=0.0,
        model_name="m",
        latency_ms=1,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert response.citations == []
