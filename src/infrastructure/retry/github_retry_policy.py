#!/usr/bin/env python3
"""
GitHub API Retry Policy.

Production-grade implementation with:
- Status code-based retry logic
- Rate limit handling with Retry-After header
- Secondary rate limit (abuse detection) handling
- Conditional request (ETag) support
"""

from typing import Optional, Dict, Any
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .retry_policy import RetryDecision, RetryClassifier


class GitHubRetryPolicy:
    """
    GitHub API-specific retry policy.
    
    GitHub API rate limits:
    - Primary: 5000 requests/hour (authenticated)
    - Secondary: Abuse detection (dynamic)
    
    Retry rules:
    - 502/503/504: Retry immediately (transient errors)
    - 403 (rate limit): Use Retry-After header
    - 401/404: Do NOT retry (auth/not found won't fix)
    - 422: Do NOT retry (validation error)
    - Abuse detection: Exponential backoff with increasing penalty
    """
    
    class GitHubStatus(Enum):
        """GitHub HTTP status codes."""
        OK = 200
        CREATED = 201
        ACCEPTED = 202
        NO_CONTENT = 204
        BAD_REQUEST = 400
        UNAUTHORIZED = 401
        FORBIDDEN = 403
        NOT_FOUND = 404
        CONFLICT = 409
        UNPROCESSABLE_ENTITY = 422
        TOO_MANY_REQUESTS = 429
        INTERNAL_SERVER_ERROR = 500
        BAD_GATEWAY = 502
        SERVICE_UNAVAILABLE = 503
        GATEWAY_TIMEOUT = 504
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Initialize GitHub retry policy.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._abuse_detection_hits = 0
        self._last_abuse_time = None
        
        logger.info(f"GitHubRetryPolicy initialized (base_delay: {base_delay}s, max_delay: {max_delay}s)")
    
    def classify_error(
        self,
        status_code: int,
        error_message: str,
        headers: Optional[Dict[str, str]] = None
    )
    -> Tuple[RetryDecision, Optional[float]]:
        """
        Classify GitHub API error for retry decision.
        
        Args:
            status_code: HTTP status code
            error_message: Error message from response
            headers: Response headers
            
        Returns:
            (RetryDecision, delay_seconds) tuple
        """
        headers = headers or {}
        
        # Check for rate limit (403 or 429)
        if status_code in {403, 429}:
            if "rate limit" in error_message.lower():
                # Use Retry-After header if available
                retry_after = self._extract_retry_after(headers)
                if retry_after is not None:
                    logger.info(f"Rate limit hit, retrying after {retry_after}s")
                    return RetryDecision.IMMEDIATE_RETRY, retry_after
                
                # Fallback: calculate based on rate limit reset
                reset_time = self._extract_rate_limit_reset(headers)
                if reset_time is not None:
                    delay = max(reset_time, self.base_delay)
                    return RetryDecision.IMMEDIATE_RETRY, delay
            
            # Check for abuse detection
            if "abuse" in error_message.lower():
                return self._handle_abuse_detection()
        
        # Transient errors - retry immediately
        if status_code in {502, 503, 504}:
            return RetryDecision.RETRY, self.base_delay
        
        # Authentication/authorization errors - do NOT retry
        if status_code in {401, 403, 404}:
            logger.warning(
                f"GitHub API error {status_code}: not retryable",
                extra={"status_code": status_code, "error": error_message}
            )
            return RetryDecision.DO_NOT_RETRY, None
        
        # Validation error - do NOT retry
        if status_code == 422:
            logger.warning(
                f"GitHub API validation error: not retryable",
                extra={"error": error_message}
            )
            return RetryDecision.DO_NOT_RETRY, None
        
        # Server errors (500) - retry with backoff
        if status_code >= 500:
            return RetryDecision.RETRY, self.base_delay * 2
        
        # Default: don't retry
        logger.warning(
            f"GitHub API error {status_code}: unknown, not retrying",
            extra={"status_code": status_code, "error": error_message}
        )
        return RetryDecision.DO_NOT_RETRY, None
    
    def _extract_retry_after(self, headers: Dict[str, str]) -> Optional[float]:
        """
        Extract Retry-After header value.
        
        Args:
            headers: Response headers
            
        Returns:
            Retry-after delay in seconds, or None
        """
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                logger.warning(f"Invalid Retry-After value: {retry_after}")
        return None
    
    def _extract_rate_limit_reset(self, headers: Dict[str, str]) -> Optional[float]:
        """
        Extract rate limit reset time from headers.
        
        Args:
            headers: Response headers
            
        Returns:
            Seconds until reset, or None
        """
        import time
        reset_time = headers.get("X-RateLimit-Reset")
        if reset_time:
            try:
                reset_timestamp = int(reset_time)
                current_timestamp = int(time.time())
                delay = max(reset_timestamp - current_timestamp, 0)
                return delay
            except (ValueError, TypeError):
                logger.warning(f"Invalid X-RateLimit-Reset value: {reset_time}")
        return None
    
    def _handle_abuse_detection(self)
    -> Tuple[RetryDecision, float]:
        """
        Handle GitHub abuse detection with exponential backoff.
        
        Returns:
            (RetryDecision, delay_seconds) tuple
        """
        import time
        
        self._abuse_detection_hits += 1
        self._last_abuse_time = time.time()
        
        # Exponential backoff for abuse detection
        # First hit: 60s, second: 120s, third: 240s, max: 3600s
        backoff = min(60 * (2 ** (self._abuse_detection_hits - 1)), 3600)
        
        logger.warning(
            f"GitHub abuse detection hit #{self._abuse_detection_hits}, "
            f"backing off for {backoff}s"
        )
        
        return RetryDecision.RETRY, backoff
    
    def reset_abuse_counter(self):
        """Reset abuse detection counter (e.g., on successful request)."""
        if self._abuse_detection_hits > 0:
            self._abuse_detection_hits = max(0, self._abuse_detection_hits - 1)
            logger.debug(f"Abuse counter decreased to {self._abuse_detection_hits}")
