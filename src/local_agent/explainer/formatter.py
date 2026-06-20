"""
Markdown formatter for an `AgentResponse` + its `Citation` list.

Produces a stable, human-readable markdown report — useful for CLI output,
IDE preview, or copy-pasting into PR comments. Output is deterministic for
the same inputs.
"""

from __future__ import annotations

from typing import Sequence

from src.local_agent.explainer.citation import Citation


class MarkdownFormatter:
    """Render `AgentResponse` + citations into a Markdown report string."""

    def format_report(self, response, citations: Sequence[Citation]) -> str:
        return _render(response, citations)


def format_report(response, citations: Sequence[Citation]) -> str:
    """Functional shorthand around MarkdownFormatter.format_report."""
    return _render(response, citations)


def _render(response, citations: Sequence[Citation]) -> str:
    sections: list[str] = []

    # Question
    sections.append(f"## Question\n\n{response.question.strip()}")

    # Answer
    answer = (response.answer or "").strip() or "_(no answer produced)_"
    sections.append(f"## Answer\n\n{answer}")

    # Citations
    if citations:
        cite_lines = ["## Citations", ""]
        for cite in citations:
            bullet = (
                f"- {cite.to_markdown()} "
                f"_(rank {cite.rank}, score {cite.score:.4f}, level {cite.level})_"
            )
            cite_lines.append(bullet)
        sections.append("\n".join(cite_lines))
    else:
        sections.append("## Citations\n\n_(no source chunks were retrieved)_")

    # Metadata
    meta_lines = [
        "## Metadata",
        "",
        f"- Confidence: **{response.confidence:.2f}**",
        f"- Model: `{response.model_name}`",
        f"- Latency: {response.latency_ms} ms",
        f"- Retrieved chunks: {response.total_retrieved} "
        f"(used: {len(response.retrieved_chunks)})",
        f"- Context tokens: {response.total_context_tokens}",
    ]
    if response.warnings:
        meta_lines.append("- Warnings:")
        meta_lines.extend(f"  - {w}" for w in response.warnings)
    sections.append("\n".join(meta_lines))

    return "\n\n".join(sections) + "\n"


__all__ = ["MarkdownFormatter", "format_report"]
