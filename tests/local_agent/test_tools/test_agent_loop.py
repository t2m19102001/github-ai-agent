"""Tests for the read-only tools and the prompt-based tool-calling loop.

All tests use a scripted fake LLM so they run without Ollama and are fully
deterministic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.local_agent.agent_loop import ToolCallingAgent
from src.local_agent.tools.base import ToolRegistry, ToolResult
from src.local_agent.tools.file_reader import FileReaderTool


class _ScriptedLLM:
    """Return pre-canned replies in order; records prompts it was given."""

    model_name = "scripted"

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.prompts: list[str] = []

    def generate(self, system_prompt, user_prompt, max_tokens=512, temperature=0.0):
        self.prompts.append(user_prompt)
        return self._replies.pop(0) if self._replies else '{"final": "done"}'


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "hello.py").write_text("print('hi')\n", encoding="utf-8")
    return tmp_path


def _registry(repo: Path) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(FileReaderTool(repo_root=repo))
    return reg


# --- FileReaderTool ---------------------------------------------------------

def test_read_file_returns_content(repo: Path) -> None:
    result = FileReaderTool(repo).run({"path": "hello.py"})
    assert result.ok
    assert "print('hi')" in result.content


def test_read_file_missing_is_failure(repo: Path) -> None:
    result = FileReaderTool(repo).run({"path": "nope.py"})
    assert not result.ok
    assert "not found" in result.content


def test_read_file_blocks_path_traversal(repo: Path) -> None:
    result = FileReaderTool(repo).run({"path": "../../etc/passwd"})
    assert not result.ok
    assert "escapes repository root" in result.content


def test_read_file_requires_path_arg(repo: Path) -> None:
    result = FileReaderTool(repo).run({})
    assert not result.ok


# --- ToolRegistry -----------------------------------------------------------

def test_registry_menu_lists_tool(repo: Path) -> None:
    menu = _registry(repo).render_menu()
    assert "read_file" in menu
    assert "path" in menu


def test_registry_rejects_duplicate(repo: Path) -> None:
    reg = _registry(repo)
    with pytest.raises(ValueError):
        reg.register(FileReaderTool(repo))


# --- ToolCallingAgent loop --------------------------------------------------

def test_loop_finishes_immediately(repo: Path) -> None:
    llm = _ScriptedLLM(['{"final": "42"}'])
    result = ToolCallingAgent(llm, _registry(repo)).run("what is the answer?")
    assert result.answer == "42"
    assert result.stopped_reason == "final"


def test_loop_calls_tool_then_finishes(repo: Path) -> None:
    llm = _ScriptedLLM(
        [
            '{"tool": "read_file", "args": {"path": "hello.py"}}',
            '{"final": "it prints hi"}',
        ]
    )
    result = ToolCallingAgent(llm, _registry(repo)).run("what does hello.py do?")
    assert result.answer == "it prints hi"
    # The tool output was fed back into the second prompt.
    assert "print('hi')" in llm.prompts[1]
    assert [s.kind for s in result.steps] == ["tool", "final"]


def test_loop_parses_json_wrapped_in_prose(repo: Path) -> None:
    llm = _ScriptedLLM(['Sure! Here you go: {"final": "answer"} hope that helps'])
    result = ToolCallingAgent(llm, _registry(repo)).run("q")
    assert result.answer == "answer"


def test_loop_reports_unknown_tool(repo: Path) -> None:
    llm = _ScriptedLLM(
        [
            '{"tool": "delete_everything", "args": {}}',
            '{"final": "recovered"}',
        ]
    )
    result = ToolCallingAgent(llm, _registry(repo)).run("q")
    assert result.answer == "recovered"
    assert "unknown tool" in llm.prompts[1]


def test_loop_short_circuits_repeated_tool_call(repo: Path) -> None:
    # Model asks for the identical read twice, then finishes. The second
    # identical call must NOT re-run the tool; it's pushed back as an error step.
    llm = _ScriptedLLM(
        [
            '{"tool": "read_file", "args": {"path": "hello.py"}}',
            '{"tool": "read_file", "args": {"path": "hello.py"}}',
            '{"final": "done reading"}',
        ]
    )
    result = ToolCallingAgent(llm, _registry(repo)).run("q")
    assert result.answer == "done reading"
    kinds = [s.kind for s in result.steps]
    assert kinds == ["tool", "error", "final"]
    assert result.steps[1].detail == "repeat:read_file"


def test_loop_stops_at_max_iters(repo: Path) -> None:
    # Always asks for a tool, never finishes → must hit the cap and stop.
    # Distinct paths each turn so every call is a genuine (non-repeat) tool run
    # and the loop stops only because it hits the iteration cap.
    llm = _ScriptedLLM(
        [f'{{"tool": "read_file", "args": {{"path": "f{i}.py"}}}}' for i in range(10)]
    )
    result = ToolCallingAgent(llm, _registry(repo), max_iters=3).run("q")
    assert result.stopped_reason == "max_iters"
    assert len([s for s in result.steps if s.kind == "tool"]) == 3


def test_loop_recovers_from_bad_json(repo: Path) -> None:
    llm = _ScriptedLLM(["not json at all", '{"final": "ok"}'])
    result = ToolCallingAgent(llm, _registry(repo)).run("q")
    assert result.answer == "ok"


def test_run_rejects_empty_question(repo: Path) -> None:
    with pytest.raises(ValueError):
        ToolCallingAgent(_ScriptedLLM([]), _registry(repo)).run("   ")


def test_tool_result_helpers() -> None:
    assert ToolResult.success("x").ok
    assert not ToolResult.failure("y").ok


def test_loop_injects_history_into_prompt(repo: Path) -> None:
    llm = _ScriptedLLM(['{"final": "yes"}'])
    history = [("user", "what is X?"), ("agent", "X is the answer")]
    result = ToolCallingAgent(llm, _registry(repo)).run("and Y?", history=history)
    assert result.answer == "yes"
    prompt = llm.prompts[0]
    assert "Previous conversation:" in prompt
    assert "what is X?" in prompt
    assert "X is the answer" in prompt


def test_loop_without_history_has_no_preamble(repo: Path) -> None:
    llm = _ScriptedLLM(['{"final": "ok"}'])
    ToolCallingAgent(llm, _registry(repo)).run("q")
    assert "Previous conversation:" not in llm.prompts[0]
