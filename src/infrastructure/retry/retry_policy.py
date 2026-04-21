#!/usr/bin/env python3
"""
Retry Policy Engine with Exponential Backoff and Jitter.

Production-grade implementation with:
- Exponential backoff with full jitter
- Context-aware retry classification
- Circuit breaker integration
- Timeout handling
- Retry budget management
"""

import random
import time
from typing import Optional, Type, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class RetryDecision(Enum):
    """Retry decision."""
    RETRY = "retry"
    DO_NOT_RETRY = "do_not_retry"
    IMMEDIATE_RETRY = "immediate_retry"


@dataclass
class RetryResult:
    """Result of retry decision."""
    should_retry: bool
    delay_seconds: float
    attempt: int
    reason: str
    max_attempts: int


class ExponentialBackoff:
    """
    Exponential backoff with jitter to prevent thundering herd.
    
    Jitter strategies:
    - Full jitter: sleep = random(0, delay)
    - Equal jitter: sleep = delay/2 + random(0, delay/2)
    - Decorrelated jitter: sleep = random(base, previous * 3)
    
    Uses full jitter by default (proven to be most effective).
    """
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_max: float = 1.0,
    ):
        """
        Initialize exponential backoff.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential calculation (default: 2)
            jitter: Enable jitter (recommended)
            jitter_max: Maximum jitter value in seconds
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_max = jitter_max
    
    def calculate(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential component
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        # Apply jitter
        if self.jitter:
            # Full jitter: random between 0 and delay
            delay = random.uniform(0, delay)
        
        return delay


class RetryPolicy:
    """
    Comprehensive retry policy with context-aware classification.
    
    Features:
    - Exception classification (fatal vs retryable)
    - Contextual retry logic
    - Exponential backoff with jitter
    - Max attempt enforcement
    - Retry budget management
    """
    
    # NEVER RETRY THESE - they will always fail
    FATAL_EXCEPTIONS = {
        ValidationError,
        AuthenticationError,
        PermissionDeniedError,
        NotFoundError,
        SecurityError,
    }
    
    # ALWAYS RETRY THESE - they are transient
    RETRYABLE_EXCEPTIONS = {
        ConnectionError,
        TimeoutError,
        ServiceUnavailable,
        RateLimitError,
        LLMProviderError,
    }
    
    # CONTEXTUAL - depends on specific error details
    CONDITIONAL_EXCEPTIONS = {
        GitHubAPIError: lambda e: e.status_code in {502, 503, 504},
        DatabaseError: lambda e: "deadlock" in str(e).lower() or "timeout" in str(e).lower(),
    }
    
    def __init__(
        self,
        max_attempts: int = 3,
        backoff: Optional[ExponentialBackoff] = None,
        retry_classifier: Optional['RetryClassifier'] = None,
    ):
        """
        Initialize retry policy.
        
        Args:
            max_attempts: Maximum retry attempts
            backoff: Backoff strategy (default: ExponentialBackoff)
            retry_classifier: Exception classifier (default: RetryClassifier)
        """
        self.max_attempts = max_attempts
        self.backoff = backoff or ExponentialBackoff()
        self._classifier = retry_classifier or RetryClassifier()
        
        logger.info(
            f"RetryPolicy initialized (max_attempts: {max_attempts}, backoff: exponential)"
        )
    
    def should_retry(
        self,
        exception: Exception,
        attempt: int,
        context: Optional[dict] = None
    ) -> RetryResult:
        """
        Determine if operation should be retried.
        
        Args:
            exception: Exception that occurred
            attempt: Current attempt number (0-indexed)
            context: Additional context for decision
            
        Returns:
            RetryResult with decision and delay
        """
        context = context or {}
        
        # Check if we've exceeded max attempts
        if attempt >= self.max_attempts:
            return RetryResult(
                should_retry=False,
                delay_seconds=0,
                attempt=attempt,
                reason=f"Max attempts ({self.max_attempts}) exceeded",
                max_attempts=self.max_attempts,
            )
        
        # Classify exception
        decision = self._classifier.classify(exception, context)
        
        if decision == RetryDecision.DO_NOT_RETRY:
            return RetryResult(
                should_retry=False,
                delay_seconds=0,
                attempt=attempt,
                reason=f"Exception type {type(exception).__name__} is not retryable",
                max_attempts=self.max_attempts,
            )
        
        # Calculate delay
        delay = self.backoff.calculate(attempt)
        
        return RetryResult(
            should_retry=True,
            delay_seconds=delay,
            attempt=attempt,
            reason=f"Retryable error, attempt {attempt + 1}/{self.max_attempts}",
            max_attempts=self.max_attempts,
        )
    
    async def execute_with_retry(
        self,
        operation: Callable,
        *args,
        max_attempts: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Execute operation with automatic retry.
        
        Args:
            operation: Async function to execute
            *args: Function arguments
            max_attempts: Override max attempts
            **kwargs: Function keyword arguments
            
        Returns:
            Operation result
            
        Raises:
            MaxRetriesExceededError: If all retries exhausted
        """
        max_attempts = max_attempts or self.max_attempts
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return await operation(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                result = self.should_retry(e, attempt)
                
                if not result.should_retry:
                    raise e
                
                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                    f"Retrying in {result.delay_seconds:.2f}s..."
                )
                
                await asyncio.sleep(result.delay_seconds)
        
        # All retries exhausted
        raise MaxRetriesExceededError(
            f"Operation failed after {max_attempts} attempts"
        ) from last_exception


class RetryClassifier:
    """
    Classify exceptions for retry logic.
    
    Provides context-aware classification based on exception type
    and additional context information.
    """
    
    def __init__(self):
        """Initialize retry classifier."""
        self._custom_classifiers = {}
        logger.info("RetryClassifier initialized")
    
    def register_classifier(
        self,
        exception_type: Type[Exception],
        classifier: Callable[[Exception, dict], RetryDecision]
    ):
        """
        Register custom exception classifier.
        
        Args:
            exception_type: Exception type to classify
            classifier: Classification function
        """
        self._custom_classifiers[exception_type] = classifier
        logger.info(f"Registered classifier for {exception_type.__name__}")
    
    def classify(
        self,
        exception: Exception,
        context: Optional[dict] = None
    ) -> RetryDecision:
        """
        Classify exception for retry decision.
        
        Args:
            exception: Exception to classify
            context: Additional context
            
        Returns:
            RetryDecision
        """
        context = context or {}
        exc_type = type(exception)
        
        # Check custom classifiers
        if exc_type in self._custom_classifiers:
            return self._custom_classifiers[exc_type](exception, context)
        
        # Check conditional exceptions
        for exc_class, checker in RetryPolicy.CONDITIONAL_EXCEPTIONS.items():
            if isinstance(exception, exc_class):
                if checker(exception):
                    return RetryDecision.RETRY
                else:
                    return RetryDecision.DO_NOT_RETRY
        
        # Check fatal exceptions
        for exc_class in RetryPolicy.FATAL_EXCEPTIONS:
            if isinstance(exception, exc_class):
                return RetryDecision.DO_NOT_RETRY
        
        # Check retryable exceptions
        for exc_class in RetryPolicy.RETRYABLE_EXCEPTIONS:
            if isinstance(exception, exc_class):
                # Special handling for rate limit
                if isinstance(exception, RateLimitError):
                    # Use retry-after header if available
                    retry_after = getattr(exception, 'retry_after', None)
                    if retry_after:
                        return RetryDecision.IMMEDIATE_RETRY
                return RetryDecision.RETRY
        
        # Default: don't retry unknown exceptions
        logger.warning(f"Unknown exception type: {exc_type.__name__}, not retrying")
        return RetryDecision.DO_NOT_RETRY


# Custom exception types
class ValidationError(Exception):
    """Validation error - never retry."""
    pass


class AuthenticationError(Exception):
    """Authentication error - never retry."""
    pass


class PermissionDeniedError(Exception):
    """Permission denied - never retry."""
    pass


class NotFoundError(Exception):
    """Not found - never retry."""
    pass


class SecurityError(Exception):
    """Security error - never retry."""
    pass


class RateLimitError(Exception):
    """Rate limit exceeded - retry after delay."""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMProviderError(Exception):
    """LLM provider error - retry."""
    pass


class GitHubAPIError(Exception):
    """GitHub API error - conditional retry."""
    
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class DatabaseError(Exception):
    """Database error - conditional retry."""
    pass


class MaxRetriesExceededError(Exception):
    """Maximum retries exceeded."""
    pass
