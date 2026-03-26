#!/usr/bin/env python3
"""Compatibility AI provider layer for legacy routes and tests."""

from __future__ import annotations

import importlib.util
import os
from abc import ABC, abstractmethod
from typing import Iterable, List, Sequence

if importlib.util.find_spec("requests"):
    import requests
else:
    requests = None

from src.core.config import GROQ_API_KEY, HUGGINGFACE_MODEL, HUGGINGFACE_TOKEN, LLM_PROVIDER
from src.llm.provider import get_llm_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProviderBase(ABC):
    """Minimal provider protocol used by the legacy web app."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    @abstractmethod
    def get_response(self, prompt: str) -> str:
        """Return a text response for a prompt."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the provider can currently serve requests."""


class GroqAIProvider(ProviderBase):
    @property
    def name(self) -> str:
        return "Groq"

    def is_available(self) -> bool:
        return bool(os.getenv("GROQ_API_KEY") or GROQ_API_KEY)

    def get_response(self, prompt: str) -> str:
        from src.llm.groq import GroqProvider

        provider = GroqProvider()
        response = provider.call([{"role": "user", "content": prompt}])
        return response or ""


class OllamaAIProvider(ProviderBase):
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def name(self) -> str:
        return "Ollama"

    def is_available(self) -> bool:
        try:
            if requests is None:
                return False
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def get_response(self, prompt: str) -> str:
        fallback = get_llm_provider("ollama")
        if hasattr(fallback, "invoke"):
            result = fallback.invoke(prompt)
            return result.content if hasattr(result, "content") else str(result)
        return f"Ollama provider unavailable for prompt: {prompt[:100]}"


class HuggingFaceAIProvider(ProviderBase):
    def __init__(self, model: str | None = None):
        self.token = os.getenv("HUGGINGFACE_TOKEN") or HUGGINGFACE_TOKEN
        self.model = model or os.getenv("HUGGINGFACE_MODEL") or HUGGINGFACE_MODEL

    @property
    def name(self) -> str:
        return "HuggingFace"

    def is_available(self) -> bool:
        return bool(self.token and self.model)

    def get_response(self, prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("HuggingFace provider is not configured")

        if requests is None:
            raise RuntimeError("requests is required for HuggingFace provider")

        response = requests.post(
            f"https://api-inference.huggingface.co/models/{self.model}",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"inputs": prompt},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            return payload[0].get("generated_text", "")
        if isinstance(payload, dict):
            return payload.get("generated_text", "") or payload.get("summary_text", "") or str(payload)
        return str(payload)


class CompositeAIProvider(ProviderBase):
    def __init__(self, providers: Sequence[ProviderBase]):
        self.providers = list(providers)

    @property
    def name(self) -> str:
        return "Composite"

    def is_available(self) -> bool:
        return any(provider.is_available() for provider in self.providers)

    def get_response(self, prompt: str) -> str:
        for provider in self.providers:
            if provider.is_available():
                return provider.get_response(prompt)
        raise RuntimeError("No AI providers are available")


class ProviderAdapter:
    """Adapts ProviderBase to the `.call(messages)` interface used by CodeChatAgent."""

    def __init__(self, provider: ProviderBase):
        self.provider = provider

    def _messages_to_prompt(self, messages: Iterable[dict] | str) -> str:
        if isinstance(messages, str):
            return messages

        parts: List[str] = []
        for message in messages:
            role = message.get("role", "user").upper()
            content = message.get("content", "")
            parts.append(f"{role}: {content}")
        return "\n\n".join(parts)

    def call(self, messages: Iterable[dict] | str) -> str:
        prompt = self._messages_to_prompt(messages)
        return self.provider.get_response(prompt)


def get_default_provider() -> ProviderBase:
    """Select the first configured provider, falling back to a mock provider."""
    provider_name = (os.getenv("LLM_PROVIDER") or LLM_PROVIDER or "").lower()

    candidates: list[ProviderBase] = []
    if provider_name == "groq":
        candidates.append(GroqAIProvider())
    elif provider_name == "huggingface":
        candidates.append(HuggingFaceAIProvider())
    elif provider_name == "ollama":
        candidates.append(OllamaAIProvider())

    candidates.extend([GroqAIProvider(), OllamaAIProvider(), HuggingFaceAIProvider()])
    composite = CompositeAIProvider(candidates)
    if composite.is_available():
        return composite

    logger.info("No external AI provider configured; falling back to mock LLM provider")

    class MockProvider(ProviderBase):
        @property
        def name(self) -> str:
            return "Mock"

        def get_response(self, prompt: str) -> str:
            provider = get_llm_provider("mock")
            return f"[{self.name}] {prompt[:200]}\n\n{provider.get_status()['status']}"

        def is_available(self) -> bool:
            return True

    return MockProvider()
