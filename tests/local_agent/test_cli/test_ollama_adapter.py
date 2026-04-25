"""Edge-case tests for the `_OllamaAdapter` defined in cli.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.local_agent.cli import _OllamaAdapter


@dataclass
class _StubProvider:
    """Stand-in for OllamaProvider; replays a queued response or raises."""

    response: Any = "ok"
    raises: Exception | None = None
    calls: list[dict] = field(default_factory=list)

    def call(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        if self.raises is not None:
            raise self.raises
        return self.response


def _adapter_with_stub(stub: _StubProvider) -> _OllamaAdapter:
    adapter = _OllamaAdapter(model_name="test-model")
    adapter._provider = stub  # bypass lazy import
    return adapter


# 1. Happy path: messages format is correct, return value passes through.
def test_generate_passes_through_provider_output() -> None:
    stub = _StubProvider(response="hello world")
    adapter = _adapter_with_stub(stub)
    result = adapter.generate(
        system_prompt="be brief",
        user_prompt="hi",
        max_tokens=100,
        temperature=0.5,
    )
    assert result == "hello world"
    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hi"},
    ]
    assert call["temperature"] == 0.5
    assert call["max_tokens"] == 100


# 2. Provider returns None → adapter raises RuntimeError with helpful message.
def test_generate_raises_when_provider_returns_none() -> None:
    stub = _StubProvider(response=None)
    adapter = _adapter_with_stub(stub)
    with pytest.raises(RuntimeError, match="Ollama returned no response"):
        adapter.generate("sys", "user")


# 3. Provider raises → adapter propagates the exception.
def test_generate_propagates_provider_exception() -> None:
    stub = _StubProvider(raises=ConnectionError("ollama down"))
    adapter = _adapter_with_stub(stub)
    with pytest.raises(ConnectionError, match="ollama down"):
        adapter.generate("sys", "user")


# 4. model_name attribute is exposed for LLMClientProtocol.
def test_model_name_attribute_set() -> None:
    adapter = _OllamaAdapter(model_name="llama3:70b")
    assert adapter.model_name == "llama3:70b"


# 5. Default kwargs map correctly.
def test_default_kwargs_used_when_not_passed() -> None:
    stub = _StubProvider(response="ok")
    adapter = _adapter_with_stub(stub)
    adapter.generate("sys", "user")  # no max_tokens / temperature
    call = stub.calls[0]
    assert call["max_tokens"] == 1200  # default
    assert call["temperature"] == 0.0  # default
