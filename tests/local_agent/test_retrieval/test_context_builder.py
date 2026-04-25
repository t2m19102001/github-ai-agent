"""P0-08 Context Builder tests."""

from __future__ import annotations

import pytest

from src.local_agent.retrieval.context_builder import (
    ContextBuilder,
    ContextMetadata,
    ContextWindow,
)
from src.local_agent.retrieval.retriever import RetrievalResult, RetrievalSource


def _make_result(
    rank: int,
    content: str = "def fn(): pass",
    *,
    chunk_id: str | None = None,
    level: str = "function",
    file_path: str | None = None,
    relative_path: str | None = None,
    score: float = 0.1,
    docstring: str | None = None,
    name: str | None = None,
    qualified_name: str | None = None,
    start_line: int = 1,
    end_line: int = 10,
) -> RetrievalResult:
    cid = chunk_id or f"c{rank}"
    return RetrievalResult(
        chunk_id=cid,
        file_path=file_path or f"/repo/{cid}.py",
        relative_path=relative_path if relative_path is not None else f"{cid}.py",
        name=name or cid,
        qualified_name=qualified_name or cid,
        level=level,
        start_line=start_line,
        end_line=end_line,
        content=content,
        docstring=docstring,
        symbols=[cid],
        parent_name=None,
        score=score,
        rank=rank,
        source=RetrievalSource.DENSE,
    )


# 1. Build succeeds with valid input.
def test_build_succeeds_with_valid_input() -> None:
    results = [_make_result(1), _make_result(2)]
    cw = ContextBuilder().build("how does fn work?", results)
    assert isinstance(cw, ContextWindow)
    assert isinstance(cw.metadata, ContextMetadata)


# 2. Formatted context includes the query.
def test_formatted_context_includes_query() -> None:
    cw = ContextBuilder().build("authentication flow", [_make_result(1)])
    assert "Query: authentication flow" in cw.formatted_context


# 3. Formatted context includes file path / line span / content / score.
def test_formatted_context_includes_metadata_fields() -> None:
    result = _make_result(
        1,
        content="def login(): pass",
        file_path="/repo/auth.py",
        relative_path="auth.py",
        start_line=42,
        end_line=88,
        score=0.1234,
        qualified_name="AuthService.login",
        level="method",
    )
    cw = ContextBuilder().build("login", [result])
    text = cw.formatted_context
    assert "File: /repo/auth.py" in text
    assert "Relative Path: auth.py" in text
    assert "Lines: 42-88" in text
    assert "def login(): pass" in text
    assert "Score: 0.1234" in text
    assert "Qualified Name: AuthService.login" in text
    assert "Level: method" in text


# 4. metadata.total_chunks reflects selected chunk count.
def test_metadata_total_chunks_correct() -> None:
    results = [_make_result(i) for i in range(1, 4)]
    cw = ContextBuilder().build("q", results)
    assert cw.metadata.total_chunks == 3


# 5. files_covered is unique and preserves first-seen order.
def test_files_covered_unique_and_ordered() -> None:
    results = [
        _make_result(1, chunk_id="a", relative_path="b.py"),
        _make_result(2, chunk_id="b", relative_path="a.py"),
        _make_result(3, chunk_id="c", relative_path="b.py"),  # dup file
    ]
    cw = ContextBuilder().build("q", results)
    assert cw.metadata.files_covered == ["b.py", "a.py"]


# 6. chunk_levels counts each level correctly.
def test_chunk_levels_count_correct() -> None:
    results = [
        _make_result(1, level="function"),
        _make_result(2, level="class"),
        _make_result(3, level="function"),
        _make_result(4, level="method"),
    ]
    cw = ContextBuilder().build("q", results)
    assert cw.metadata.chunk_levels == {"function": 2, "class": 1, "method": 1}


# 7. total_tokens equals heuristic sum across selected chunks.
def test_total_tokens_consistent_with_heuristic() -> None:
    results = [
        _make_result(1, content="x" * 40),  # 10 tokens
        _make_result(2, content="y" * 80),  # 20 tokens
    ]
    cw = ContextBuilder().build("q", results)
    assert cw.total_tokens == 10 + 20
    assert cw.total_tokens == cw.metadata.total_tokens


# 8. Dedupe by chunk_id keeps the best-rank instance.
def test_dedupe_keeps_best_rank() -> None:
    results = [
        _make_result(2, chunk_id="dup", content="rank2"),
        _make_result(1, chunk_id="dup", content="rank1"),  # better rank
        _make_result(3, chunk_id="other", content="other"),
    ]
    cw = ContextBuilder().build("q", results)
    chunk_ids = [c.chunk_id for c in cw.chunks]
    assert chunk_ids.count("dup") == 1
    dup_chunk = next(c for c in cw.chunks if c.chunk_id == "dup")
    assert dup_chunk.content == "rank1"
    assert dup_chunk.rank == 1


# 9. Final order follows ascending rank after dedupe.
def test_preserves_rank_order_after_dedupe() -> None:
    results = [
        _make_result(3, chunk_id="c"),
        _make_result(1, chunk_id="a"),
        _make_result(2, chunk_id="b"),
        _make_result(4, chunk_id="a"),  # dup, should be dropped
    ]
    cw = ContextBuilder().build("q", results)
    assert [c.chunk_id for c in cw.chunks] == ["a", "b", "c"]


# 10. Token budget truncates at chunk boundary.
def test_token_budget_truncates_at_chunk_boundary() -> None:
    # Each chunk is 40 chars => 10 tokens. Budget 25 tokens => fit 2 chunks (20).
    results = [_make_result(i, content="x" * 40) for i in range(1, 5)]
    builder = ContextBuilder(max_tokens=25, reserve_tokens=0)
    cw = builder.build("q", results)
    assert len(cw.chunks) == 2
    assert cw.total_tokens == 20


# 11. First chunk that exceeds budget is still included (no crash, no empty).
def test_first_chunk_oversize_still_included() -> None:
    # 400 chars => 100 tokens, but budget is 5.
    results = [
        _make_result(1, content="x" * 400),
        _make_result(2, content="y" * 40),
    ]
    builder = ContextBuilder(max_tokens=5, reserve_tokens=0)
    cw = builder.build("q", results)
    assert len(cw.chunks) == 1
    assert cw.chunks[0].chunk_id == "c1"
    assert cw.total_tokens == 100  # honest accounting, even past budget


# 12. Empty / whitespace query raises ValueError.
@pytest.mark.parametrize("bad_query", ["", "   ", "\n\t"])
def test_empty_query_raises(bad_query: str) -> None:
    with pytest.raises(ValueError):
        ContextBuilder().build(bad_query, [_make_result(1)])


# 13. Empty retrieval results list raises ValueError.
def test_empty_results_raises() -> None:
    with pytest.raises(ValueError):
        ContextBuilder().build("q", [])


# 14. to_prompt_fragment() returns formatted_context unchanged.
def test_to_prompt_fragment_returns_formatted_context() -> None:
    cw = ContextBuilder().build("q", [_make_result(1)])
    assert cw.to_prompt_fragment() == cw.formatted_context


# 15. Deterministic: same input produces identical formatted_context.
def test_deterministic_same_input_same_output() -> None:
    results = [_make_result(i, content=f"body-{i}") for i in range(1, 5)]
    a = ContextBuilder().build("q", results)
    b = ContextBuilder().build("q", results)
    assert a.formatted_context == b.formatted_context
    assert a.total_tokens == b.total_tokens


# B1. assembly_time_ms is non-negative.
def test_assembly_time_ms_is_non_negative() -> None:
    cw = ContextBuilder().build("q", [_make_result(1)])
    assert cw.metadata.assembly_time_ms >= 0


# B2. Constructor rejects bad max_tokens / reserve_tokens.
@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"max_tokens": 0}, "max_tokens"),
        ({"max_tokens": -1}, "max_tokens"),
        ({"reserve_tokens": -5}, "reserve_tokens"),
    ],
)
def test_invalid_max_tokens_raises(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ContextBuilder(**kwargs)


# Bonus: docstring rendered when present, omitted when None.
def test_docstring_rendered_when_present() -> None:
    cw = ContextBuilder().build(
        "q", [_make_result(1, docstring="explains the function")]
    )
    assert "Docstring:" in cw.formatted_context
    assert "explains the function" in cw.formatted_context


def test_docstring_omitted_when_absent() -> None:
    cw = ContextBuilder().build("q", [_make_result(1, docstring=None)])
    assert "Docstring:" not in cw.formatted_context


# Bonus: per-call max_tokens override takes precedence over constructor.
def test_per_call_max_tokens_overrides_constructor() -> None:
    results = [_make_result(i, content="x" * 40) for i in range(1, 5)]  # 10 tokens each
    builder = ContextBuilder(max_tokens=999, reserve_tokens=0)  # would fit all
    cw = builder.build("q", results, max_tokens=25)  # tighter override
    assert len(cw.chunks) == 2
