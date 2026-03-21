#!/usr/bin/env python3
"""
AI Provider Module
Wrapper for LLM providers with adapter pattern
"""

from typing import Dict, Any, Optional, List
import os

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

try:
    from src.llm.groq import GroqProvider
except ImportError:
    GroqProvider = None

try:
    from src.llm.provider import LLMProvider
except ImportError:
    LLMProvider = object

logger = get_logger(__name__)


def get_default_provider() -> LLMProvider:
    """Get the default LLM provider based on environment config"""
    provider_name = os.getenv("LLM_PROVIDER", "groq").lower()
    
    if provider_name == "groq" and GroqProvider:
        return GroqProvider()
    
    if provider_name == "ollama":
        try:
            from src.llm.ollama import OllamaProvider
            return OllamaProvider()
        except ImportError:
            pass
    
    return MockProvider()


class ProviderAdapter:
    """Adapter wrapper for LLM providers"""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.name = provider.name if hasattr(provider, 'name') else "unknown"
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using the underlying provider"""
        if hasattr(self.provider, 'generate_async'):
            return await self.provider.generate_async(prompt, **kwargs)
        elif hasattr(self.provider, 'generate_response'):
            return await self.provider.generate_response(prompt, **kwargs)
        else:
            return f"Mock response for: {prompt[:100]}"
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status"""
        if hasattr(self.provider, 'get_status'):
            return self.provider.get_status()
        return {
            "name": self.name,
            "status": "active"
        }


class MockProvider:
    """Mock provider for testing/development"""
    
    name = "mock"
    
    def __init__(self):
        logger.info("Initialized Mock LLM provider")
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        return f"Mock response for: {prompt[:100]}..."
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        return await self.generate_response(prompt, **kwargs)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "active",
            "type": "mock"
        }


__all__ = ["get_default_provider", "ProviderAdapter", "MockProvider"]
