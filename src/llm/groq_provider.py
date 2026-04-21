#!/usr/bin/env python3
"""
Groq Primary Provider.

Production-grade implementation with:
- Groq API integration
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
    ProviderRateLimitError,
    ProviderAuthenticationError,
    LLMProviderError,
)

logger = get_logger(__name__)


class GroqProvider(LLMProvider):
    """
    Groq LLM provider (primary).
    
    Groq provides fast inference with open-source models.
    """
    
    API_BASE = "https://api.groq.com/openai/v1"
    
    def __init__(self, api_key: str, timeout: int = 30):
        """
        Initialize Groq provider.
        
        Args:
            api_key: Groq API key
            timeout: Request timeout in seconds
        """
        super().__init__(name="groq", api_key=api_key)
        self.timeout = timeout
        self._http_client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
        )
        
        logger.info(f"GroqProvider initialized (timeout: {timeout}s)")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from Groq.
        
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
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
            }
            
            # Make API call
            response = await self._http_client.post(
                f"{self.API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract response
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "stop")
            
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            tokens_used = prompt_tokens + completion_tokens
            
            latency_ms = (time.time() - start_time) * 1000
            
            return LLMResponse(
                content=content,
                model=data["model"],
                provider=self.name,
                finish_reason=finish_reason,
                tokens_used=tokens_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                metadata={"request_id": data.get("id")},
            )
            
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(f"Groq request timed out: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    f"Groq rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else None
                )
            elif e.response.status_code == 401:
                raise ProviderAuthenticationError("Groq authentication failed")
            else:
                raise LLMProviderError(f"Groq API error: {e.response.status_code}")
        except Exception as e:
            raise LLMProviderError(f"Groq request failed: {e}")
    
    async def health_check(self) -> bool:
        """
        Check Groq health.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._http_client.get(
                f"{self.API_BASE}/models",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
        logger.info("GroqProvider closed")
