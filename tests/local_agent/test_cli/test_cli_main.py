"""CLI tests for the `query` subcommand. Use agent_factory injection for hermeticity."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest

from src.local_agent import cli as cli_module
from src.local_agent.core import AgentResponse, QueryConfig


def _make_response(
    question: str = "what does X do?",
    answer: str = "Overview:\n- X does Y\n\nKey points:\n- it returns Z",
    *,
    warnings: list[str] | None = None,
    confidence: float = 0.75,
    latency_ms: int = 42,
) -> AgentResponse:
    return AgentResponse(
        question=question,
        answer=answer,
        retrieved_chunks=["chunk-a", "chunk-b"],
        total_retrieved=2,
        total_context_tokens=12,
        confidence=confidence,
        model_name="fake-model",
        latency_ms=latency_ms,
        timestamp=datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc),
        warnings=warnings if warnings is not None else [],
    )


@dataclass
class FakeAgent:
    response: AgentResponse
    raises: Exception | None = None
    calls: list[str] = field(default_factory=list)

    def query(self, question: str) -> AgentResponse:
        # Mirror LocalAgent.query() validation so CLI tests exercise the
        # real ValueError → exit-code-2 path.
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty, non-whitespace string")
        self.calls.append(question)
        if self.raises is not None:
            raise self.raises
        return self.response


def _make_factory(agent: FakeAgent, recorded: list[QueryConfig]):
    def factory(*, config: QueryConfig, index_dir: str, model_name: str):
        recorded.append(config)
        return agent

    return factory


def _run_query(
    extra_argv: list[str],
    *,
    agent: FakeAgent | None = None,
    recorded: list[QueryConfig] | None = None,
) -> tuple[int, str, str]:
    """Invoke the `query` subcommand with captured stdio."""
    out = io.StringIO()
    err = io.StringIO()
    factory = None
    if agent is not None:
        factory = _make_factory(agent, recorded if recorded is not None else [])
    code = cli_module.main(
        ["query", *extra_argv],
        agent_factory=factory,
        stdout=out,
        stderr=err,
    )
    return code, out.getvalue(), err.getvalue()


# 1. --help exits 0 with usage text (top-level).
def test_top_level_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.main(["--help"])
    assert exc.value.code == 0


# 1b. `query --help` works.
def test_query_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.main(["query", "--help"])
    assert exc.value.code == 0


# 2. Happy path: agent.query called once with the question argument.
def test_happy_path_calls_query_once() -> None:
    agent = FakeAgent(response=_make_response())
    code, _, _ = _run_query(["how does login work?"], agent=agent)
    assert code == 0
    assert agent.calls == ["how does login work?"]


# 3. Human-readable output contains Question + Answer headers.
def test_human_readable_output_contains_headers() -> None:
    agent = FakeAgent(response=_make_response())
    code, stdout, _ = _run_query(["q"], agent=agent)
    assert code == 0
    assert "Question:" in stdout
    assert "Answer:" in stdout
    assert "Confidence:" in stdout
    assert "Model: fake-model" in stdout


# 4. --json emits valid JSON containing the key fields.
def test_json_mode_outputs_parseable_json() -> None:
    agent = FakeAgent(response=_make_response())
    code, stdout, _ = _run_query(["--json", "q"], agent=agent)
    assert code == 0
    payload = json.loads(stdout)
    assert payload["question"] == "what does X do?"
    assert payload["answer"].startswith("Overview")
    assert payload["confidence"] == 0.75
    assert payload["model_name"] == "fake-model"
    assert payload["latency_ms"] == 42
    assert payload["timestamp"].startswith("2026-04-25T12:00:00")


# 5. --version prints version and exits 0 without invoking the agent.
def test_version_flag_exits_without_running_agent() -> None:
    agent = FakeAgent(response=_make_response())
    with pytest.raises(SystemExit) as exc:
        cli_module.main(["--version"], agent_factory=lambda **_: agent)
    assert exc.value.code == 0
    assert agent.calls == []


# 6. Empty question → exit code 2 with error message on stderr.
def test_empty_question_exits_with_error() -> None:
    agent = FakeAgent(response=_make_response())
    code, _, stderr = _run_query(["   "], agent=agent)
    assert code == 2
    assert "non-empty" in stderr.lower() or "non-whitespace" in stderr.lower()


# 7. Unexpected exception from agent.query → exit 1 + error on stderr.
def test_query_unexpected_exception_exits_with_error() -> None:
    agent = FakeAgent(response=_make_response(), raises=RuntimeError("index missing"))
    code, _, stderr = _run_query(["q"], agent=agent)
    assert code == 1
    assert "query failed" in stderr.lower()
    assert "index missing" in stderr


# 8. -k and --max-context-tokens map into QueryConfig passed to factory.
def test_flags_map_into_query_config() -> None:
    agent = FakeAgent(response=_make_response())
    recorded: list[QueryConfig] = []
    code, _, _ = _run_query(
        ["-k", "5", "--max-context-tokens", "1000", "q"],
        agent=agent,
        recorded=recorded,
    )
    assert code == 0
    assert recorded[0].top_k == 5
    assert recorded[0].max_context_tokens == 1000


# 9. Deterministic stdout for the same input.
def test_deterministic_output_for_same_input() -> None:
    response = _make_response()
    _, out_a, _ = _run_query(["q"], agent=FakeAgent(response=response))
    _, out_b, _ = _run_query(["q"], agent=FakeAgent(response=response))
    assert out_a == out_b


# Bonus: agent factory failure → exit 1.
def test_agent_factory_failure_exits_with_error() -> None:
    out = io.StringIO()
    err = io.StringIO()

    def bad_factory(**_):
        raise RuntimeError("missing FAISS index")

    code = cli_module.main(
        ["query", "q"], agent_factory=bad_factory, stdout=out, stderr=err
    )
    assert code == 1
    assert "failed to initialize agent" in err.getvalue().lower()
    assert "missing faiss index" in err.getvalue().lower()


# Bonus: --verbose surfaces context info + warnings.
def test_verbose_flag_includes_context_block() -> None:
    agent = FakeAgent(
        response=_make_response(warnings=["llm_error:RuntimeError:timeout"])
    )
    code, stdout, _ = _run_query(["-v", "q"], agent=agent)
    assert code == 0
    assert "Retrieved chunks: 2" in stdout
    assert "Context tokens: 12" in stdout
    assert "chunk-a" in stdout
    assert "Warnings:" in stdout
    assert "llm_error" in stdout


# Bonus: warnings are surfaced even without --verbose (compact section).
def test_non_verbose_still_shows_warnings_section() -> None:
    agent = FakeAgent(response=_make_response(warnings=["retriever returned no results"]))
    code, stdout, _ = _run_query(["q"], agent=agent)
    assert code == 0
    assert "Warnings:" in stdout
    assert "retriever returned no results" in stdout


# Bonus: factory receives the model name and index dir from CLI.
def test_factory_receives_model_and_index_dir() -> None:
    agent = FakeAgent(response=_make_response())
    captured: dict = {}

    def factory(*, config, index_dir, model_name):
        captured.update(config=config, index_dir=index_dir, model_name=model_name)
        return agent

    code = cli_module.main(
        ["query", "--model", "llama3:70b", "--index-dir", "/tmp/idx", "q"],
        agent_factory=factory,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert code == 0
    assert captured["model_name"] == "llama3:70b"
    assert captured["index_dir"] == "/tmp/idx"


# Bonus: invoking with no subcommand fails with non-zero exit.
def test_missing_subcommand_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.main([], stdout=io.StringIO(), stderr=io.StringIO())
    assert exc.value.code != 0
