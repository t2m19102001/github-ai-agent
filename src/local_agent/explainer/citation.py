"""
Citation linker — convert RetrievalResults into renderable Citation records.

A `Citation` is a frozen, JSON-friendly snapshot of "which chunk from where",
ready to be embedded in markdown answers, JSON payloads, or IDE links.

Inputs are read; nothing is mutated. Output order matches input order so
downstream consumers can preserve retrieval ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Citation:
    """A single source pointer renderable as text or markdown."""

    chunk_id: str
    relative_path: str | None
    file_path: str
    name: str | None
    qualified_name: str | None
    level: str
    start_line: int
    end_line: int
    score: float
    rank: int

    def display_path(self) -> str:
        """Prefer relative path for display; fall back to absolute."""
        return self.relative_path or self.file_path

    def to_markdown(self) -> str:
        """Render as a Markdown link: `[name (file.py:42-88)](file.py#L42-L88)`.

        Labels are escaped so brackets cannot terminate the link text early,
        and destinations containing spaces or parens are wrapped in `<...>`
        per CommonMark so the URL does not break.
        """
        path = self.display_path()
        anchor = f"#L{self.start_line}-L{self.end_line}"
        label_name = self.qualified_name or self.name or path
        label = _escape_label(f"{label_name} ({path}:{self.start_line}-{self.end_line})")
        return f"[{label}]({_markdown_destination(path + anchor)})"

    def to_text(self) -> str:
        """Plain-text variant for non-markdown outputs."""
        path = self.display_path()
        label = self.qualified_name or self.name
        prefix = f"{label} — " if label else ""
        return f"{prefix}{path}:{self.start_line}-{self.end_line}"


class CitationLinker:
    """Builds Citation records from a list of retrieval results."""

    def link(self, chunks: Sequence) -> list[Citation]:
        """Convert each input chunk to a Citation, preserving order."""
        return [_chunk_to_citation(item) for item in chunks]


def link_chunks(chunks: Iterable) -> list[Citation]:
    """Functional shorthand around `CitationLinker.link`."""
    return CitationLinker().link(list(chunks))


def _escape_label(text: str) -> str:
    """Escape characters that would break out of a markdown link's text span."""
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _markdown_destination(dest: str) -> str:
    """Wrap a link destination in <...> when it contains spaces or parens.

    Bare markdown URLs cannot contain whitespace or unbalanced parens; the
    angle-bracket form is the CommonMark-sanctioned way to carry them. Plain
    destinations are returned unchanged so ordinary paths stay clean.
    """
    if any(ch in dest for ch in " ()<>"):
        # Inside <...>, only < and > need escaping.
        escaped = dest.replace("\\", "\\\\").replace("<", "\\<").replace(">", "\\>")
        return f"<{escaped}>"
    return dest


def _chunk_to_citation(chunk) -> Citation:
    return Citation(
        chunk_id=chunk.chunk_id,
        relative_path=chunk.relative_path,
        file_path=chunk.file_path,
        name=chunk.name,
        qualified_name=chunk.qualified_name,
        level=chunk.level,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        score=float(chunk.score),
        rank=int(chunk.rank),
    )


__all__ = ["Citation", "CitationLinker", "link_chunks"]
