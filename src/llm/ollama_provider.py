#!/usr/bin/env python3
"""
Ollama Local Fallback Provider.

Production-grade implementation with:
- Ollama API integration (local)
- Timeout protection
- Error handling
- Token counting
"""

import asyncio
import time
from typing import Optional
import httpx

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .provider_interface import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderTimeoutError,
    LLMProviderError,
)

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama LLM provider (local fallback).
    
    Ollama provides local inference with open-source models.
    Used as fallback when cloud providers are unavailable.
    """
    
    API_BASE = "http://localhost:11434/api"
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 60):
        """
        Initialize Ollama provider.
        
        Args:
            base_url: Ollama API base URL
            timeout: Request timeout in seconds (longer for local inference)
        """
        super().__init__(name="ollama", api_key=None)
        self.base_url = base_url
        self.timeout = timeout
        self._http_client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2)
        )
        
        logger.info(f"OllamaProvider initialized (base_url: {base_url}, timeout: {timeout}s)")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from Ollama.
        
        Args:
            request: LLM request
            
        Returns:
            LLM response
            
        Raises:
            LLMProviderError: If generation fails
        """
        start_time = time.time()
        
        try:
            # Build request
            messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.messages
            ]
            
            payload = {
                "model": request.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                    "top_p": request.top_p,
                },
            }
            
            # Make API call
            response = await self._http_client.post(
                f"{self.base_url}/chat",
                headers={
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract response
            message = data["message"]
            content = message["content"]
            
            # Ollama doesn't provide token counts, estimate
            # Rough estimation: ~4 chars per token
            estimated_tokens = len(content) // 4
            prompt_tokens = len(str(messages)) // 4
            completion_tokens = estimated_tokens
            tokens_used = prompt_tokens + completion_tokens
            
            latency_ms = (time.time() - start_time) * 1000
            
            return LLMResponse(
                content=content,
                model=request.model,
                provider=self.name,
                finish_reason="stop",
                tokens_used=tokens_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                metadata={"evaluated_tokens": True},
            )
            
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(f"Ollama request timed out: {e}")
        except httpx.ConnectError as e:
            raise LLMProviderError(f"Ollama connection failed: {e}")
        except httpx.HTTPStatusError as e:
            raise LLMProviderError(f"Ollama API error: {e.response.status_code}")
        except Exception as e:
            raise LLMProviderError(f"Ollama request failed: {e}")
    
    async def health_check(self) -> bool:
        """
        Check Ollama health.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._http_client.get(f"{self.base_url}/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
        logger.info("OllamaProvider closed")
