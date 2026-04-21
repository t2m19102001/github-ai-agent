#!/usr/bin/env python3
"""
LLM Provider Retry Policy.

Production-grade implementation with:
- Provider-specific retry logic
- Context length error handling
- Rate limit handling
- Fallback chain support
"""

from typing import Optional, Dict, Any
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .retry_policy import RetryDecision


class LLMRetryPolicy:
    """
    LLM provider-specific retry policy.
    
    LLM provider error handling:
    - Timeout: Retry with exponential backoff
    - Rate limit: Use provider's reset time
    - Content policy violation: Do NOT retry
    - Context length exceeded: Do NOT retry (needs different strategy)
    - Service unavailable: Retry with backoff
    """
    
    class LLMErrorType(Enum):
        """LLM error types."""
        TIMEOUT = "timeout"
        RATE_LIMIT = "rate_limit"
        CONTENT_POLICY = "content_policy"
        CONTEXT_LENGTH = "context_length"
        SERVICE_UNAVAILABLE = "service_unavailable"
        AUTHENTICATION = "authentication"
        UNKNOWN = "unknown"
    
    def __init__(self, base_delay: float = 2.0, max_delay: float = 120.0):
        """
        Initialize LLM retry policy.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        logger.info(f"LLMRetryPolicy initialized (base_delay: {base_delay}s, max_delay: {max_delay}s)")
    
    def classify_error(
        self,
        error_type: LLMErrorType,
        error_message: str,
        provider: Optional[str] = None,
        retry_after: Optional[float] = None
    )
    -> Tuple[RetryDecision, Optional[float]]:
        """
        Classify LLM error for retry decision.
        
        Args:
            error_type: Type of LLM error
            error_message: Error message
            provider: LLM provider name
            retry_after: Suggested retry delay (if provided by provider)
            
        Returns:
            (RetryDecision, delay_seconds) tuple
        """
        provider = provider or "unknown"
        
        # Content policy violation - do NOT retry
        if error_type == self.LLMErrorType.CONTENT_POLICY:
            logger.warning(
                f"LLM content policy violation: not retryable",
                extra={"provider": provider, "error": error_message}
            )
            return RetryDecision.DO_NOT_RETRY, None
        
        # Context length exceeded - do NOT retry
        if error_type == self.LLMErrorType.CONTEXT_LENGTH:
            logger.warning(
                f"LLM context length exceeded: not retryable",
                extra={"provider": provider, "error": error_message}
            )
            return RetryDecision.DO_NOT_RETRY, None
        
        # Authentication error - do NOT retry
        if error_type == self.LLMErrorType.AUTHENTICATION:
            logger.error(
                f"LLM authentication error: not retryable",
                extra={"provider": provider, "error": error_message}
            )
            return RetryDecision.DO_NOT_RETRY, None
        
        # Rate limit - use retry_after if provided
        if error_type == self.LLMErrorType.RATE_LIMIT:
            if retry_after is not None:
                logger.info(
                    f"LLM rate limit, retrying after {retry_after}s",
                    extra={"provider": provider}
                )
                return RetryDecision.IMMEDIATE_RETRY, retry_after
            
            # Fallback to exponential backoff
            delay = min(self.base_delay * 2, self.max_delay)
            return RetryDecision.RETRY, delay
        
        # Timeout - retry with backoff
        if error_type == self.LLMErrorType.TIMEOUT:
            delay = min(self.base_delay * 2, self.max_delay)
            logger.info(
                f"LLM timeout, retrying after {delay}s",
                extra={"provider": provider}
            )
            return RetryDecision.RETRY, delay
        
        # Service unavailable - retry with backoff
        if error_type == self.LLMErrorType.SERVICE_UNAVAILABLE:
            delay = min(self.base_delay * 3, self.max_delay)
            logger.info(
                f"LLM service unavailable, retrying after {delay}s",
                extra={"provider": provider}
            )
            return RetryDecision.RETRY, delay
        
        # Unknown error - do NOT retry (safe default)
        logger.warning(
            f"Unknown LLM error: not retrying",
            extra={"provider": provider, "error": error_message}
        )
        return RetryDecision.DO_NOT_RETRY, None
    
    def detect_error_type(self, error_message: str, status_code: Optional[int] = None) -> LLMErrorType:
        """
        Detect LLM error type from error message and status code.
        
        Args:
            error_message: Error message
            status_code: HTTP status code (if applicable)
            
        Returns:
            Detected error type
        """
        error_message_lower = error_message.lower()
        
        # Check for content policy violations
        if any(term in error_message_lower for term in [
            "content policy",
            "safety policy",
            "violation",
            "blocked",
        ]):
            return self.LLMErrorType.CONTENT_POLICY
        
        # Check for context length errors
        if any(term in error_message_lower for term in [
            "context length",
            "max tokens",
            "token limit",
            "too long",
        ]):
            return self.LLMErrorType.CONTEXT_LENGTH
        
        # Check for rate limit errors
        if any(term in error_message_lower for term in [
            "rate limit",
            "too many requests",
            "quota exceeded",
        ]) or status_code == 429:
            return self.LLMErrorType.RATE_LIMIT
        
        # Check for authentication errors
        if any(term in error_message_lower for term in [
            "authentication",
            "unauthorized",
            "invalid api key",
        ]) or status_code == 401:
            return self.LLMErrorType.AUTHENTICATION
        
        # Check for timeout errors
        if any(term in error_message_lower for term in [
            "timeout",
            "timed out",
        ]) or status_code == 504:
            return self.LLMErrorType.TIMEOUT
        
        # Check for service unavailable
        if status_code in {502, 503}:
            return self.LLMErrorType.SERVICE_UNAVAILABLE
        
        # Default to unknown
        return self.LLMErrorType.UNKNOWN
