"""
BM25 sparse retriever — keyword search to complement dense (FAISS) retrieval.

Dense embeddings capture *meaning* but can miss exact tokens (a rare function
name, an error string). BM25 is the classic keyword-ranking algorithm: it scores
a document by how often the query's terms appear in it, damped so common terms
and long documents don't dominate. Together, dense + BM25 (fused in hybrid.py)
catch more than either alone.

Implemented from scratch (~standard BM25) to avoid a new dependency and to keep
the algorithm visible: for each query term t and document d,

    score += idf(t) * (f(t,d) * (k1+1)) / (f(t,d) + k1*(1 - b + b*|d|/avgdl))

where f(t,d) is the term's count in d, |d| the doc length, avgdl the average,
and idf(t) the inverse document frequency. k1 and b are the usual knobs.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_K1 = 1.5  # term-frequency saturation
_B = 0.75  # length-normalisation strength


def tokenize(text: str) -> list[str]:
    """Lowercase word/identifier tokens — snake_case and digits kept intact."""
    return _TOKEN_RE.findall(text.lower())


@dataclass
class _Doc:
    tokens: list[str]
    counts: Counter
    length: int


class BM25Index:
    """A small in-memory BM25 index over a fixed list of documents."""

    def __init__(self, documents: list[str]) -> None:
        self._docs: list[_Doc] = []
        df: Counter = Counter()  # document frequency per term
        for text in documents:
            toks = tokenize(text)
            counts = Counter(toks)
            self._docs.append(_Doc(tokens=toks, counts=counts, length=len(toks)))
            for term in counts:  # each term counted once per doc
                df[term] += 1

        n = len(self._docs)
        self._avgdl = (sum(d.length for d in self._docs) / n) if n else 0.0
        # Smoothed idf; +1 inside log keeps it positive even for common terms.
        self._idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def score(self, query: str, doc_index: int) -> float:
        doc = self._docs[doc_index]
        if doc.length == 0:
            return 0.0
        total = 0.0
        for term in tokenize(query):
            if term not in doc.counts:
                continue
            idf = self._idf.get(term, 0.0)
            freq = doc.counts[term]
            denom = freq + _K1 * (1 - _B + _B * doc.length / (self._avgdl or 1))
            total += idf * (freq * (_K1 + 1)) / denom
        return total

    def top_k(self, query: str, k: int) -> list[tuple[int, float]]:
        """Return (doc_index, score) for the k best docs, score-descending."""
        scored = [
            (i, self.score(query, i)) for i in range(len(self._docs))
        ]
        scored = [pair for pair in scored if pair[1] > 0.0]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


__all__ = ["BM25Index", "tokenize"]
