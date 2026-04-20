#!/usr/bin/env python3
"""Lightweight completion agent used by legacy tests and demos."""

from __future__ import annotations

import re
from typing import Dict, List


class CodeCompletionAgent:
    def __init__(self):
        self.common_method_suggestions = ["json()", "text", "status_code", "raise_for_status()"]

    def _detect_completion_type(self, code_before: str, _full_context: str) -> str:
        snippet = code_before.rstrip()
        if snippet.startswith("import ") or snippet.startswith("from "):
            return "import"
        if snippet.startswith("class "):
            return "class"
        if snippet.startswith("#"):
            return "comment"
        if snippet.endswith("."):
            return "method"
        if re.search(r"def\s+[A-Za-z_0-9]*$", snippet):
            return "function"
        if snippet.endswith("="):
            return "variable"
        return "general"

    def complete(self, code_before: str, language: str = "python", max_suggestions: int = 3) -> List[Dict]:
        completion_type = self._detect_completion_type(code_before, code_before)
        suggestions: List[str]

        if completion_type == "import":
            suggestions = ["os", "sys", "typing"]
        elif completion_type == "function":
            suggestions = ["summary", "discount", "average"]
        elif completion_type == "class":
            suggestions = ["def __repr__(self):", "def to_dict(self):", "def validate(self):"]
        elif completion_type == "method":
            suggestions = self.common_method_suggestions
        elif completion_type == "variable":
            suggestions = ["None", "0", "{}"]
        else:
            suggestions = ["pass", "return None", "# TODO"]

        return [
            {"text": suggestion, "confidence": max(0.4, 0.9 - (idx * 0.1)), "type": completion_type}
            for idx, suggestion in enumerate(suggestions[:max_suggestions])
        ]

    def complete_inline(self, file_content: str, cursor_line: int, cursor_column: int, language: str = "python") -> List[Dict]:
        lines = file_content.splitlines()
        current_line = lines[cursor_line] if 0 <= cursor_line < len(lines) else ""
        prefix = current_line[:cursor_column]
        return self.complete(prefix, language=language, max_suggestions=3)
