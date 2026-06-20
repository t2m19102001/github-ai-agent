#!/usr/bin/env python3
"""Unified LLM provider module.

This module acts as the single provider factory for the rest of the codebase.
It intentionally exposes a provider implementation compatible with both:
1) legacy async agent calls (`generate_async`)
2) provider-style calls used by concrete integrations (`call`)
"""

from typing import Dict, Any, List, Optional, Union

from src.agents.base import LLMProvider as BaseLLMProvider

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMProvider(BaseLLMProvider):
    """Default provider implementation used in local/dev and tests."""

    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        model: str = "mock",
    ):
        super().__init__(name=name, model=model)
        self.config = config or {}
        logger.info(f"Initialized LLM provider: {name} ({model})")

    def call(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Synchronous provider contract used by LLMProvider subclasses."""
        prompt = " ".join(m.get("content", "") for m in messages if isinstance(m, dict))
        prompt = prompt.strip()
        if not prompt:
            return "Mock response"
        return f"Mock response for: {prompt[:100]}..."

    def get_available_models(self) -> List[str]:
        return ["mock"]

    async def generate_response(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        **kwargs,
    ) -> str:
        """Async helper for legacy agent flows."""
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
        return self.call(messages, **kwargs) or ""

    async def generate_async(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        **kwargs,
    ) -> str:
        """Async alias retained for backward compatibility."""
        return await self.generate_response(prompt, **kwargs)

    def get_status(self) -> Dict[str, Any]:
        return {"name": self.name, "status": "active", "config": self.config}


def get_llm_provider(provider_name: str = "mock", config: Dict[str, Any] = None):
    """Get an LLM provider instance.

    Routes a provider name to a concrete implementation:
      - "mock" (default): offline echo provider, no network.
      - "groq": real Groq cloud API (needs GROQ_API_KEY in env/.env).
      - "ollama": real local Ollama (needs `ollama serve` + a pulled model).
      - "failover": try Ollama first, then Groq, then mock.

    Any unknown name or import/construction failure falls back to mock so the
    caller never crashes on an unconfigured provider.
    """
    name = (provider_name or "mock").lower()

    if name == "mock":
        return LLMProvider("mock", config)

    try:
        if name == "groq":
            from src.llm.groq import GroqProvider
            return GroqProvider()
        if name == "ollama":
            from src.llm.ollama import OllamaProvider
            return OllamaProvider()
        if name == "failover":
            from src.llm.failover import FailoverProvider
            from src.llm.ollama import OllamaProvider
            from src.llm.groq import GroqProvider
            return FailoverProvider([
                OllamaProvider(),
                GroqProvider(),
                LLMProvider("mock", config),
            ])
    except Exception as e:
        logger.warning(f"Provider '{name}' init failed ({e}); using mock")
        return LLMProvider("mock", config)

    logger.warning(f"Unknown provider '{name}'; using mock")
    return LLMProvider("mock", config)
