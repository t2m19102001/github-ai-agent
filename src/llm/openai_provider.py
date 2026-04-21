#!/usr/bin/env python3
"""
OpenAI Backup Provider.

Production-grade implementation with:
- OpenAI API integration
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


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM provider (backup).
    
    OpenAI provides GPT models as backup when Groq is unavailable.
    """
    
    API_BASE = "https://api.openai.com/v1"
    
    def __init__(self, api_key: str, timeout: int = 30):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            timeout: Request timeout in seconds
        """
        super().__init__(name="openai", api_key=api_key)
        self.timeout = timeout
        self._http_client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
        )
        
        logger.info(f"OpenAIProvider initialized (timeout: {timeout}s)")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from OpenAI.
        
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
            raise ProviderTimeoutError(f"OpenAI request timed out: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    f"OpenAI rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else None
                )
            elif e.response.status_code == 401:
                raise ProviderAuthenticationError("OpenAI authentication failed")
            else:
                raise LLMProviderError(f"OpenAI API error: {e.response.status_code}")
        except Exception as e:
            raise LLMProviderError(f"OpenAI request failed: {e}")
    
    async def health_check(self) -> bool:
        """
        Check OpenAI health.
        
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
            logger.error(f"OpenAI health check failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
        logger.info("OpenAIProvider closed")
