#!/usr/bin/env python3
"""
Workflow Retry Handler.

Production-grade implementation with:
- Retry logic for workflow steps
- Exponential backoff
- Max retry limits
- Retry-safe operations
"""

import asyncio
from typing import Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_backoff: bool = True
    jitter: bool = True


class WorkflowRetryHandler:
    """
    Workflow retry handler.
    
    Handles retries for workflow steps with exponential backoff.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry handler.
        
        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        
        logger.info(f"WorkflowRetryHandler initialized (max_retries: {self.config.max_retries})")
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with retry logic.
        
        Args:
            operation: Operation to execute
            operation_name: Name of operation for logging
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Operation result
            
        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None
        delay = self.config.base_delay
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = await operation(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Operation succeeded on attempt {attempt + 1}: {operation_name}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    # Calculate delay
                    if self.config.exponential_backoff:
                        delay = min(delay * 2, self.config.max_delay)
                    
                    # Add jitter
                    if self.config.jitter:
                        import random
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{self.config.max_retries + 1}): {operation_name}. "
                        f"Retrying in {delay:.2f}s. Error: {e}"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Operation failed after {self.config.max_retries + 1} attempts: {operation_name}. "
                        f"Final error: {e}"
                    )
        
        # All retries exhausted
        raise last_exception
    
    def is_retryable(self, exception: Exception) -> bool:
        """
        Check if exception is retryable.
        
        Uses whitelist approach - only specific transient errors are retryable.
        
        Args:
            exception: Exception to check
            
        Returns:
            True if retryable, False otherwise
        """
        # Retryable exceptions (transient failures)
        retryable_exceptions = [
            # Network/connection errors
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            # HTTP client errors
            Exception,  # Placeholder for httpx.NetworkError, httpx.TimeoutException
            # Database transient errors
            Exception,  # Placeholder for sqlalchemy.exc.OperationalError
            # Custom retryable errors
            Exception,  # Placeholder for custom RetryableError
        ]
        
        # Check for specific retryable types
        if isinstance(exception, (TimeoutError, asyncio.TimeoutError)):
            return True
        
        # Check for connection-related errors in message
        error_str = str(exception).lower()
        retryable_keywords = [
            'timeout', 'connection', 'network', 'temporary', 'transient',
            'unavailable', 'retry', 'refused', 'reset', 'broken pipe',
            '503', '502', '504', '429'  # HTTP status codes
        ]
        
        if any(keyword in error_str for keyword in retryable_keywords):
            return True
        
        # Non-retryable by default (fail fast for application errors)
        return False
