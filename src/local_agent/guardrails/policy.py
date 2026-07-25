"""
Guardrails for the tool-calling loop — safety checks tuned to *this* agent.

FileGuardrails (validators.py) guards file *writes*; this agent is read-only, so
its real risks are different:

* **Unsafe tool call** — a tool invoked with dangerous input (a path escaping
  the repo, a git action beyond the read-only whitelist). We block these
  *before* the tool runs — defence in depth on top of each tool's own checks.
* **Ungrounded answer** — the model returns a final answer without ever running
  a tool. It may be fabricated, so we flag it (warn, don't block).
* **Prompt injection** — a file the agent read contains text like "ignore your
  instructions". We flag it so a downstream reviewer knows the transcript may
  be tainted.

Severity drives behaviour: ``block=True`` findings stop the action; ``block=
False`` findings are warnings attached to the result but let it proceed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# git actions the git_reader tool is allowed to run (mirrors the tool's own
# whitelist; kept here so the policy is a single, auditable place).
_ALLOWED_GIT_ACTIONS = {"log", "diff"}

# Cheap heuristics for instructions smuggled inside file content.
_INJECTION_PATTERNS = (
    re.compile(r"ignore (all|previous|your) instructions", re.IGNORECASE),
    re.compile(r"disregard (the|all|previous)", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
)


@dataclass(frozen=True)
class GuardFinding:
    """One guardrail result. ``block`` True means the action must not proceed."""

    ok: bool
    message: str
    block: bool = False

    @classmethod
    def allow(cls) -> "GuardFinding":
        return cls(ok=True, message="", block=False)

    @classmethod
    def warn(cls, message: str) -> "GuardFinding":
        return cls(ok=False, message=message, block=False)

    @classmethod
    def deny(cls, message: str) -> "GuardFinding":
        return cls(ok=False, message=message, block=True)


def check_tool_call(tool_name: str, args: dict) -> GuardFinding:
    """Validate a tool call before it runs. Denies clearly unsafe input."""
    if not isinstance(args, dict):
        return GuardFinding.deny(f"args for {tool_name!r} must be an object")

    # A path argument must be repo-relative — never absolute, never traversing.
    path = args.get("path")
    if isinstance(path, str) and _looks_unsafe_path(path):
        return GuardFinding.deny(f"unsafe path argument: {path!r}")

    # git_reader must stay within its read-only action whitelist.
    if tool_name == "git_reader":
        action = args.get("action", "log")
        if action not in _ALLOWED_GIT_ACTIONS:
            return GuardFinding.deny(f"git action not allowed: {action!r}")

    return GuardFinding.allow()


def check_final_answer(answer: str, tool_calls_made: int) -> GuardFinding:
    """Warn when a final answer is not grounded in any tool observation."""
    if tool_calls_made == 0:
        return GuardFinding.warn(
            "answer produced without running any tool — it may be ungrounded"
        )
    if not answer.strip():
        return GuardFinding.warn("answer is empty")
    return GuardFinding.allow()


def check_observation(content: str) -> GuardFinding:
    """Warn if tool output appears to contain prompt-injection instructions."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(content):
            return GuardFinding.warn(
                "tool output may contain injected instructions "
                f"(matched: {pattern.pattern!r})"
            )
    return GuardFinding.allow()


def _looks_unsafe_path(path: str) -> bool:
    """True for absolute paths or any component that climbs out of the tree."""
    if path.startswith("/") or path.startswith("~"):
        return True
    parts = path.replace("\\", "/").split("/")
    return ".." in parts


__all__ = [
    "GuardFinding",
    "check_final_answer",
    "check_observation",
    "check_tool_call",
]
