"""
search_code tool — semantic + keyword search over the indexed codebase.

This is what fuses RAG into the tool-calling agent. read_file needs a known
path; search_code answers "where is the code about X?" by querying the hybrid
(dense + BM25) retriever and returning the top chunks with their locations.

With this tool the agent chooses its own strategy each turn: search the index
to find relevant code, then read_file to see a whole file — instead of RAG being
a fixed one-shot step. That self-directed choice is the mature-agent pattern.

The retriever is injected lazily and cached, so building the registry stays
cheap and the embedding model loads only if the agent actually searches.
"""

from __future__ import annotations

from pathlib import Path

from src.local_agent.tools.base import ToolResult

_MAX_HITS = 6
_SNIPPET_CHARS = 240


class SearchCodeTool:
    """Retrieve relevant code chunks for a natural-language query."""

    name = "search_code"
    description = "Search the indexed codebase for code relevant to a query."
    args_schema = {"query": "what to look for, e.g. 'where is the retry logic'"}

    def __init__(self, index_dir: Path | str, model_name: str) -> None:
        self.index_dir = Path(index_dir).expanduser()
        self.model_name = model_name
        self._retriever = None

    def _get_retriever(self):
        if self._retriever is None:
            from src.local_agent.retrieval.hybrid import HybridRetriever

            self._retriever = HybridRetriever(
                index_dir=self.index_dir, model_name=self.model_name
            )
        return self._retriever

    def run(self, args: dict) -> ToolResult:
        query = args.get("query")
        if not query or not isinstance(query, str):
            return ToolResult.failure("search_code needs a string 'query' argument")

        try:
            hits = self._get_retriever().retrieve(query, k=_MAX_HITS)
        except FileNotFoundError:
            return ToolResult.failure(
                "no code index found — build one with `cli index .` first"
            )
        except Exception as error:  # keep the loop alive on retriever errors
            return ToolResult.failure(f"search failed: {error}")

        if not hits:
            return ToolResult.failure(f"no code found for {query!r}")

        lines: list[str] = []
        for hit in hits:
            loc = hit.relative_path or hit.file_path
            snippet = hit.content.strip().replace("\n", " ")[:_SNIPPET_CHARS]
            lines.append(f"{loc}:{hit.start_line}-{hit.end_line}: {snippet}")
        return ToolResult.success("\n".join(lines))


__all__ = ["SearchCodeTool"]
