"""Compatibility package for provider abstractions used by legacy FastAPI/chat modules."""

from .ai_provider import (
    CompositeAIProvider,
    GroqAIProvider,
    HuggingFaceAIProvider,
    OllamaAIProvider,
    ProviderAdapter,
    ProviderBase,
    get_default_provider,
)

__all__ = [
    "CompositeAIProvider",
    "GroqAIProvider",
    "HuggingFaceAIProvider",
    "OllamaAIProvider",
    "ProviderAdapter",
    "ProviderBase",
    "get_default_provider",
]
