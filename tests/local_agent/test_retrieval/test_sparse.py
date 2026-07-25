"""Tests for the from-scratch BM25 sparse index."""

from __future__ import annotations

from src.local_agent.retrieval.sparse import BM25Index, tokenize


def test_tokenize_lowercases_and_keeps_identifiers() -> None:
    assert tokenize("Foo_Bar baz123!") == ["foo_bar", "baz123"]


def test_ranks_document_with_query_terms_first() -> None:
    docs = [
        "the cat sat on the mat",
        "database connection pooling logic",
        "authentication and login flow",
    ]
    index = BM25Index(docs)
    hits = index.top_k("database connection", k=3)
    assert hits  # something matched
    assert hits[0][0] == 1  # the database doc ranks first


def test_no_match_returns_empty() -> None:
    index = BM25Index(["alpha beta", "gamma delta"])
    assert index.top_k("zzz nonexistent", k=5) == []


def test_rare_term_scores_higher_than_common() -> None:
    # "login" appears in one doc; "the" in all — rare term should dominate.
    docs = [
        "the login handler validates the token",
        "the cache the store the queue",
        "the parser the lexer the tree",
    ]
    index = BM25Index(docs)
    hits = index.top_k("login", k=3)
    assert hits[0][0] == 0


def test_top_k_limit_respected() -> None:
    docs = [f"term{i} shared" for i in range(10)]
    index = BM25Index(docs)
    hits = index.top_k("shared", k=3)
    assert len(hits) == 3


def test_empty_document_scores_zero() -> None:
    index = BM25Index(["", "real content here"])
    assert index.score("content", 0) == 0.0
