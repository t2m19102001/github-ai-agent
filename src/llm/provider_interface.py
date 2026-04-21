#!/usr/bin/env python3
"""
LLM Provider Interface (Abstraction Layer).

Production-grade implementation with:
- Provider abstraction
- Request/Response models
- Timeout protection
- Error handling
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class ModelRole(Enum):
    """Model role in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """Message in conversation."""
    role: ModelRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMRequest:
    """LLM request."""
    model: str
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 30  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """LLM response."""
    content: str
    model: str
    provider: str
    finish_reason: str
    tokens_used: int
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "finish_reason": self.finish_reason,
            "tokens_used": self.tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class ProviderTimeoutError(LLMProviderError):
    """Exception raised when provider times out."""
    pass


class ProviderRateLimitError(LLMProviderError):
    """Exception raised when provider rate limit is hit."""
    pass


class ProviderAuthenticationError(LLMProviderError):
    """Exception raised when provider authentication fails."""
    pass


class LLMProvider(ABC):
    """
    Abstract LLM provider interface.
    
    All providers must implement this interface for consistency.
    """
    
    def __init__(self, name: str, api_key: Optional[str] = None):
        """
        Initialize provider.
        
        Args:
            name: Provider name
            api_key: API key (if required)
        """
        self.name = name
        self.api_key = api_key
        self._is_available = True
        
        logger.info(f"LLMProvider initialized: {name}")
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from LLM.
        
        Args:
            request: LLM request
            
        Returns:
            LLM response
            
        Raises:
            LLMProviderError: If generation fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check provider health.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._is_available
    
    def mark_unavailable(self):
        """Mark provider as unavailable (for circuit breaker)."""
        self._is_available = False
        logger.warning(f"Provider marked as unavailable: {self.name}")
    
    def mark_available(self):
        """Mark provider as available (for circuit breaker recovery)."""
        self._is_available = True
        logger.info(f"Provider marked as available: {self.name}")
