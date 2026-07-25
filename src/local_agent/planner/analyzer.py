"""
Goal Analyzer Module.

Purpose: Analyze goals and retrieved repository state for planning.
"""

from __future__ import annotations

from typing import Any, Iterable

class GoalAnalyzer:
    """Analyzes goals and current state."""
    
    def analyze(self, goal: str, context) -> dict:
        """
        Analyze goal and context.
        
        Args:
            goal: Implementation goal
            context: Current codebase context
            
        Returns:
            Analysis results
        """
        normalized = " ".join((goal or "").split())
        if len(normalized) < 10:
            raise ValueError("goal must contain at least 10 characters")

        chunks: Iterable[Any]
        if hasattr(context, "chunks"):
            chunks = context.chunks
        else:
            chunks = context or []

        files = []
        symbols = []
        for chunk in chunks:
            path = getattr(chunk, "relative_path", None) or getattr(chunk, "file_path", None)
            if path and path not in files:
                files.append(path)
            symbol = getattr(chunk, "qualified_name", None) or getattr(chunk, "name", None)
            if symbol and symbol not in symbols:
                symbols.append(symbol)

        return {
            "goal": normalized,
            "files": files,
            "symbols": symbols,
            "retrieved_chunks": len(list(chunks)) if isinstance(chunks, list) else None,
            "requires_clarification": not files,
        }
