"""
Explainer Module.

Purpose: Format agent output with citations and confidence.
Input: Plan or response
Output: Markdown with file:line citations

Components:
    formatter: Markdown formatting
    citation: Source linking
    confidence: Confidence scoring
"""

from src.local_agent.explainer.formatter import MarkdownFormatter, format_report
from src.local_agent.explainer.citation import Citation, CitationLinker, link_chunks
from src.local_agent.explainer.confidence import ConfidenceScorer

__all__ = [
    "Citation",
    "CitationLinker",
    "MarkdownFormatter",
    "ConfidenceScorer",
    "link_chunks",
    "format_report",
]
