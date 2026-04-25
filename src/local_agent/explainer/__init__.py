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

from src.local_agent.explainer.formatter import MarkdownFormatter
from src.local_agent.explainer.citation import CitationLinker
from src.local_agent.explainer.confidence import ConfidenceScorer

__all__ = ["MarkdownFormatter", "CitationLinker", "ConfidenceScorer"]
