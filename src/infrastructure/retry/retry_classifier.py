#!/usr/bin/env python3
"""
Retry Classifier - Context-Aware Exception Classification.

Production-grade implementation with:
- Exception type classification
- Context-aware decision making
- Custom classifier registration
- Logging for audit trail
"""

from typing import Optional, Dict, Any, Type, Callable
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


class RetryClassifier:
    """
    Classify exceptions for retry logic.
    
    Provides context-aware classification based on:
    - Exception type
    - Exception attributes
    - Context information (e.g., HTTP status codes)
    - Custom classifiers
    """
    
    # Default classification rules
    DEFAULT_FATAL_EXCEPTIONS = {
        'ValidationError',
        'AuthenticationError',
        'PermissionDeniedError',
        'NotFoundError',
        'SecurityError',
    }
    
    DEFAULT_RETRYABLE_EXCEPTIONS = {
        'ConnectionError',
        'TimeoutError',
        'ServiceUnavailable',
        'RateLimitError',
        'LLMProviderError',
    }
    
    def __init__(self):
        """Initialize retry classifier."""
        self._custom_classifiers: Dict[Type[Exception], Callable] = {}
        logger.info("RetryClassifier initialized")
    
    def register_classifier(
        self,
        exception_type: Type[Exception],
        classifier: Callable[[Exception, Dict[str, Any]], RetryDecision]
    ):
        """
        Register custom exception classifier.
        
        Args:
            exception_type: Exception type to classify
            classifier: Classification function
        """
        self._custom_classifiers[exception_type] = classifier
        logger.info(f"Registered custom classifier for {exception_type.__name__}")
    
    def classify(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> RetryDecision:
        """
        Classify exception for retry decision.
        
        Args:
            exception: Exception to classify
            context: Additional context information
            
        Returns:
            RetryDecision
        """
        context = context or {}
        exc_type_name = type(exception).__name__
        
        # Check custom classifiers first
        for exc_type, classifier in self._custom_classifiers.items():
            if isinstance(exception, exc_type):
                decision = classifier(exception, context)
                logger.debug(
                    f"Custom classifier for {exc_type_name}: {decision.value}",
                    extra={"exception": str(exception), "context": context}
                )
                return decision
        
        # Check default fatal exceptions
        if exc_type_name in self.DEFAULT_FATAL_EXCEPTIONS:
            logger.debug(
                f"{exc_type_name} is fatal (non-retryable)",
                extra={"exception": str(exception)}
            )
            return RetryDecision.DO_NOT_RETRY
        
        # Check default retryable exceptions
        if exc_type_name in self.DEFAULT_RETRYABLE_EXCEPTIONS:
            logger.debug(
                f"{exc_type_name} is retryable",
                extra={"exception": str(exception)}
            )
            
            # Special handling for rate limit
            if hasattr(exception, 'retry_after'):
                retry_after = getattr(exception, 'retry_after')
                if retry_after is not None:
                    logger.debug(f"Rate limit with retry_after: {retry_after}s")
                    return RetryDecision.IMMEDIATE_RETRY
            
            return RetryDecision.RETRY
        
        # Default: don't retry unknown exceptions
        logger.warning(
            f"Unknown exception type: {exc_type_name}, defaulting to DO_NOT_RETRY",
            extra={"exception": str(exception)}
        )
        return RetryDecision.DO_NOT_RETRY
