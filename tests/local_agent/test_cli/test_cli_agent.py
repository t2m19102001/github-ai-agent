"""CLI tests for the `agent` (tool-calling) subcommand.

The loop and tools are tested directly elsewhere; here we verify the CLI wires
argv → ToolCallingAgent correctly, without touching Ollama (we monkeypatch the
LLM adapter with a scripted fake).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

import src.local_agent.cli as cli_module


class _ScriptedLLM:
    model_name = "scripted"

    def __init__(self, *_args, **_kwargs) -> None:
        self._replies = ['{"final": "the answer is 7"}']

    def generate(self, system_prompt, user_prompt, max_tokens=512, temperature=0.0):
        return self._replies.pop(0) if self._replies else '{"final": "done"}'


def _run(argv, monkeypatch, repo: Path):
    # Replace the real Ollama adapter with a scripted fake.
    monkeypatch.setattr(cli_module, "_OllamaAdapter", _ScriptedLLM)
    out, err = io.StringIO(), io.StringIO()
    code = cli_module.main(
        argv + ["--repo-root", str(repo)], stdout=out, stderr=err
    )
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


def test_agent_returns_answer(monkeypatch, repo: Path) -> None:
    code, stdout, _ = _run(["agent", "what is the answer?"], monkeypatch, repo)
    assert code == 0
    assert "the answer is 7" in stdout


def test_agent_verbose_shows_steps(monkeypatch, repo: Path) -> None:
    code, stdout, _ = _run(
        ["agent", "-v", "what is the answer?"], monkeypatch, repo
    )
    assert code == 0
    assert "Steps:" in stdout
    assert "final" in stdout


def test_agent_rejects_bad_repo_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_module, "_OllamaAdapter", _ScriptedLLM)
    out, err = io.StringIO(), io.StringIO()
    code = cli_module.main(
        ["agent", "q", "--repo-root", str(tmp_path / "nope")],
        stdout=out,
        stderr=err,
    )
    assert code == 2
    assert "not a directory" in err.getvalue()


def test_agent_empty_question_exits_two(monkeypatch, repo: Path) -> None:
    code, _, err = _run(["agent", "   "], monkeypatch, repo)
    assert code == 2
