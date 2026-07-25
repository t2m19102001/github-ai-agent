"""
Prompt-based tool-calling loop — the difference between a *chatbot* and an *agent*.

`LocalAgent.query` (core.py) is one-shot RAG: retrieve context, ask the LLM
once, done. This loop adds the missing ingredient of an *agent*: the LLM can
decide it needs more information, ask to run a tool, see the result, and try
again — repeating until it can answer.

Why "prompt-based" instead of Ollama's native function-calling API? Small local
models (0.5b–3b) that run on a plain CPU do not support the tools API reliably.
So we do it by hand, which is also the clearest way to *see* how tool-calling
works underneath every framework:

    1. Show the LLM a menu of tools and a strict reply protocol.
    2. The LLM replies with ONE JSON object per turn:
         {"tool": "read_file", "args": {"path": "src/foo.py"}}   → run a tool
         {"final": "the answer"}                                 → stop
    3. We parse that JSON, run the tool, append the result to the transcript,
       and loop. A max-iteration cap guarantees termination.

The LLM never touches the filesystem — it only *asks*; this module is the sole
place a tool actually runs, so every capability stays auditable and read-only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from pathlib import Path

from src.local_agent.core import LLMClientProtocol
from src.local_agent.tools.base import ToolRegistry, ToolResult
from src.local_agent.tools.code_query import CodeQueryTool
from src.local_agent.tools.file_reader import FileReaderTool
from src.local_agent.tools.git_reader import GitReaderTool
from src.local_agent.tools.list_files import ListFilesTool

_DEFAULT_MAX_ITERS = 4

_SYSTEM_PROMPT_TEMPLATE = (
    "You are a code assistant that can call tools to inspect a repository.\n\n"
    "Available tools:\n{menu}\n\n"
    "On EVERY turn reply with exactly ONE JSON object and nothing else.\n"
    "To call a tool:  {{\"tool\": \"<name>\", \"args\": {{...}}}}\n"
    "To finish:       {{\"final\": \"<your answer>\"}}\n"
    "Call a tool only when you need more information. Prefer to finish once you "
    "can answer. Never invent file paths you have not seen."
)


@dataclass
class LoopStep:
    """One turn of the loop, recorded so callers can inspect the agent's path."""

    kind: str  # "tool" or "final" or "error"
    detail: str  # tool name, or the final answer, or an error message
    tool_output: str | None = None


@dataclass
class LoopResult:
    """Outcome of running the loop: the answer plus a full trace for learning."""

    answer: str
    steps: list[LoopStep] = field(default_factory=list)
    stopped_reason: str = "final"  # "final" | "max_iters"


class ToolCallingAgent:
    """Drive an LLM through a read → decide → act → observe loop."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        registry: ToolRegistry,
        max_iters: int = _DEFAULT_MAX_ITERS,
    ) -> None:
        self.llm = llm_client
        self.registry = registry
        self.max_iters = max_iters

    def run(self, question: str) -> LoopResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(menu=self.registry.render_menu())
        # The transcript is the agent's growing short-term memory for this task.
        transcript = f"Question: {question}\n"
        steps: list[LoopStep] = []

        for _ in range(self.max_iters):
            raw = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=transcript + "\nYour JSON reply:",
                max_tokens=512,
                temperature=0.0,
            )
            decision = _parse_decision(raw)

            if decision is None:
                # The model broke protocol; tell it so and let it retry.
                steps.append(LoopStep(kind="error", detail="unparseable reply"))
                transcript += (
                    "\nSystem: Your last reply was not valid JSON. Reply with a "
                    "single JSON object as instructed.\n"
                )
                continue

            if "final" in decision:
                answer = str(decision["final"]).strip()
                steps.append(LoopStep(kind="final", detail=answer))
                return LoopResult(answer=answer, steps=steps, stopped_reason="final")

            # Otherwise it's a tool call.
            tool_name = str(decision.get("tool", ""))
            tool_args = decision.get("args") or {}
            result = self._run_tool(tool_name, tool_args)
            steps.append(
                LoopStep(kind="tool", detail=tool_name, tool_output=result.content)
            )
            status = "OK" if result.ok else "ERROR"
            transcript += (
                f"\nAction: called {tool_name} with {json.dumps(tool_args)}\n"
                f"Observation ({status}): {result.content}\n"
            )

        # Ran out of iterations without a final answer.
        return LoopResult(
            answer="I could not complete the task within the step budget.",
            steps=steps,
            stopped_reason="max_iters",
        )

    def _run_tool(self, name: str, args: dict) -> ToolResult:
        tool = self.registry.get(name)
        if tool is None:
            available = ", ".join(self.registry.names()) or "(none)"
            return ToolResult.failure(
                f"unknown tool {name!r}. Available: {available}"
            )
        if not isinstance(args, dict):
            return ToolResult.failure(f"args for {name!r} must be an object")
        return tool.run(args)


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_decision(raw: str) -> dict | None:
    """Extract the first JSON object from a possibly chatty LLM reply.

    Small models often wrap JSON in prose or code fences, so we grab the first
    ``{...}`` span rather than demanding the whole reply be pure JSON.
    """
    if not isinstance(raw, str):
        return None
    match = _JSON_OBJECT_RE.search(raw)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def build_default_registry(repo_root: Path | str) -> ToolRegistry:
    """Registry with every read-only tool wired to ``repo_root``.

    Central place the CLI (and any caller) uses so the tool set stays
    consistent everywhere.
    """
    registry = ToolRegistry()
    registry.register(ListFilesTool(repo_root))
    registry.register(FileReaderTool(repo_root))
    registry.register(CodeQueryTool(repo_root))
    registry.register(GitReaderTool(repo_root))
    return registry


__all__ = [
    "LoopResult",
    "LoopStep",
    "ToolCallingAgent",
    "build_default_registry",
]
