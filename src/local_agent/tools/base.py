"""
Tool contract for the local agent's prompt-based tool-calling loop.

A *tool* is a small, read-only capability the LLM can ask to run when the
retrieved context is not enough — e.g. "read the whole of file X". The loop
(see ``agent_loop.py``) shows the LLM a menu of tools, the LLM replies with a
JSON ``{"tool": ..., "args": {...}}`` request, and the loop executes the
matching tool and feeds the result back.

Design rules (kept deliberately strict for a learning codebase):

* Tools are **read-only**. They never modify the repository or the system.
* Every tool declares ``name``, ``description`` and an ``args_schema`` (a plain
  ``{arg: help}`` dict) so the loop can render a self-documenting menu.
* ``run(args)`` always returns a ``ToolResult`` — success or failure — and never
  raises for expected problems (missing file, bad args). It only raises for
  genuine programmer errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ToolResult:
    """Outcome of a single tool invocation.

    ``ok`` says whether the tool succeeded; ``content`` is the text handed back
    to the LLM (the file body, the git log, or an error message). Keeping
    failures inside ToolResult — instead of raising — lets the agent loop show
    the LLM *why* a tool failed so it can recover on the next turn.
    """

    ok: bool
    content: str

    @classmethod
    def success(cls, content: str) -> "ToolResult":
        return cls(ok=True, content=content)

    @classmethod
    def failure(cls, message: str) -> "ToolResult":
        return cls(ok=False, content=message)


@runtime_checkable
class Tool(Protocol):
    """Structural type every tool must satisfy.

    Using a Protocol (not a base class) means a tool just needs these four
    members — no inheritance required — which keeps each tool file independent.
    """

    name: str
    description: str
    args_schema: dict[str, str]

    def run(self, args: dict) -> ToolResult: ...


class ToolRegistry:
    """A name → Tool lookup plus a rendered menu for the LLM prompt."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name!r}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def render_menu(self) -> str:
        """Human-readable catalogue injected into the system prompt."""
        if not self._tools:
            return "(no tools available)"
        lines: list[str] = []
        for name in self.names():
            tool = self._tools[name]
            arg_desc = ", ".join(
                f"{arg} ({help_})" for arg, help_ in tool.args_schema.items()
            ) or "(no arguments)"
            lines.append(f"- {name}: {tool.description}\n    args: {arg_desc}")
        return "\n".join(lines)


__all__ = ["Tool", "ToolRegistry", "ToolResult"]
