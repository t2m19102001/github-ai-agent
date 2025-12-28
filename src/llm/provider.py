#!/usr/bin/env python3
"""
LLM Provider Module
Provides LLM functionality for agents
"""

import asyncio
from typing import Dict, Any, Optional

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMProvider:
    """Base LLM provider class"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        logger.info(f"Initialized LLM provider: {name}")
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM"""
        # Mock implementation for testing
        return f"Mock response for: {prompt[:100]}..."
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM (async alias)"""
        return await self.generate_response(prompt, **kwargs)
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status"""
        return {
            "name": self.name,
            "status": "active",
            "config": self.config
        }


def get_llm_provider(provider_name: str = "mock", config: Dict[str, Any] = None) -> LLMProvider:
    """Get LLM provider instance"""
    return LLMProvider(provider_name, config)
