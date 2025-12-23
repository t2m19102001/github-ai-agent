#!/usr/bin/env python3
import os
import types
import pytest

from src.agent.ai_provider import (
    ProviderBase,
    GroqAIProvider,
    OllamaAIProvider,
    HuggingFaceAIProvider,
    ProviderAdapter,
    CompositeAIProvider,
)


def test_groq_is_available(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "dummy")
    p = GroqAIProvider()
    assert p.is_available() is True


def test_ollama_is_available(monkeypatch):
    import src.agent.ai_provider as ai

    class Resp:
        status_code = 200

    def fake_get(url, timeout=2):
        return Resp()

    monkeypatch.setattr(ai, "requests", types.SimpleNamespace(get=fake_get))
    p = OllamaAIProvider()
    assert p.is_available() is True


def test_provider_adapter_calls(monkeypatch):
    class Dummy(ProviderBase):
        @property
        def name(self):
            return "Dummy"
        def get_response(self, prompt: str) -> str:
            return "ok"
        def is_available(self) -> bool:
            return True

    base = Dummy()
    adapter = ProviderAdapter(base)
    msg = [{"role": "user", "content": "Hello"}]
    out = adapter.call(msg)
    assert isinstance(out, str)
    assert out == "ok"


def test_huggingface_get_response(monkeypatch):
    import src.agent.ai_provider as ai

    class Resp:
        def __init__(self):
            self._json = [{"generated_text": "hello"}]
        def raise_for_status(self):
            return None
        def json(self):
            return self._json

    def fake_post(url, headers=None, json=None, timeout=30):
        return Resp()

    monkeypatch.setenv("HUGGINGFACE_TOKEN", "token")
    monkeypatch.setenv("HUGGINGFACE_MODEL", "model")
    monkeypatch.setattr(ai, "requests", types.SimpleNamespace(post=fake_post))
    p = HuggingFaceAIProvider()
    assert p.is_available() is True
    assert p.get_response("hi") == "hello"
