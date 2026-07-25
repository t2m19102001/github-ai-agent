"""
Explainer Module.

Purpose: Format agent output with citations.
Input: Plan or response
Output: Markdown with file:line citations

Components:
    formatter: Markdown formatting
    citation: Source linking
"""

from src.local_agent.explainer.formatter import MarkdownFormatter, format_report
from src.local_agent.explainer.citation import Citation, CitationLinker, link_chunks

__all__ = [
    "Citation",
    "CitationLinker",
    "MarkdownFormatter",
    "link_chunks",
    "format_report",
]
