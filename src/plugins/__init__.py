"""Compatibility package for legacy `src.agent.*` imports."""

from .ai_provider import (
    CompositeAIProvider,
    GroqAIProvider,
    HuggingFaceAIProvider,
    OllamaAIProvider,
    ProviderAdapter,
    ProviderBase,
    get_default_provider,
)
from .plugins import (
    AutoCheckCodeQualityPlugin,
    AutoCommentOnIssuePlugin,
    PluginBase,
    PluginManager,
)

__all__ = [
    "CompositeAIProvider",
    "GroqAIProvider",
    "HuggingFaceAIProvider",
    "OllamaAIProvider",
    "ProviderAdapter",
    "ProviderBase",
    "get_default_provider",
    "PluginBase",
    "PluginManager",
    "AutoCheckCodeQualityPlugin",
    "AutoCommentOnIssuePlugin",
]
