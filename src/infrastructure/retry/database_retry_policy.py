#!/usr/bin/env python3
"""
Database Retry Policy.

Production-grade implementation with:
- Deadlock detection and retry
- Connection timeout handling
- Transaction timeout handling
- Statement timeout handling
"""

from typing import Optional, Dict, Any
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .retry_policy import RetryDecision


class DatabaseRetryPolicy:
    """
    Database-specific retry policy.
    
    Database error handling:
    - Deadlock: Retry immediately (1 attempt only)
    - Connection timeout: Retry with exponential backoff
    - Statement timeout: Do NOT retry (query needs optimization)
    - Constraint violation: Do NOT retry (data issue)
    - Connection lost: Retry with exponential backoff
    """
    
    class DBErrorType(Enum):
        """Database error types."""
        DEADLOCK = "deadlock"
        CONNECTION_TIMEOUT = "connection_timeout"
        STATEMENT_TIMEOUT = "statement_timeout"
        CONSTRAINT_VIOLATION = "constraint_violation"
        CONNECTION_LOST = "connection_lost"
        UNKNOWN = "unknown"
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 30.0):
        """
        Initialize database retry policy.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        logger.info(f"DatabaseRetryPolicy initialized (base_delay: {base_delay}s, max_delay: {max_delay}s)")
    
    def classify_error(
        self,
        error_type: DBErrorType,
        error_message: str,
        attempt: int = 0
    )
    -> Tuple[RetryDecision, Optional[float]]:
        """
        Classify database error for retry decision.
        
        Args:
            error_type: Type of database error
            error_message: Error message
            attempt: Current attempt number
            
        Returns:
            (RetryDecision, delay_seconds) tuple
        """
        # Deadlock - retry immediately but only once
        if error_type == self.DBErrorType.DEADLOCK:
            if attempt < 1:
                logger.info("Deadlock detected, retrying immediately (attempt 1 of 1)")
                return RetryDecision.RETRY, 0  # Immediate retry
            else:
                logger.warning("Deadlock persisted after retry, giving up")
                return RetryDecision.DO_NOT_RETRY, None
        
        # Statement timeout - do NOT retry (needs query optimization)
        if error_type == self.DBErrorType.STATEMENT_TIMEOUT:
            logger.warning(
                "Statement timeout: not retryable (query needs optimization)",
                extra={"error": error_message}
            )
            return RetryDecision.DO_NOT_RETRY, None
        
        # Constraint violation - do NOT retry (data issue)
        if error_type == self.DBErrorType.CONSTRAINT_VIOLATION:
            logger.warning(
                "Constraint violation: not retryable (data issue)",
                extra={"error": error_message}
            )
            return RetryDecision.DO_NOT_RETRY, None
        
        # Connection timeout - retry with backoff
        if error_type == self.DBErrorType.CONNECTION_TIMEOUT:
            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
            logger.info(
                f"Connection timeout, retrying after {delay}s",
                extra={"attempt": attempt + 1}
            )
            return RetryDecision.RETRY, delay
        
        # Connection lost - retry with backoff
        if error_type == self.DBErrorType.CONNECTION_LOST:
            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
            logger.info(
                f"Connection lost, retrying after {delay}s",
                extra={"attempt": attempt + 1}
            )
            return RetryDecision.RETRY, delay
        
        # Unknown error - do NOT retry (safe default)
        logger.warning(
            f"Unknown database error: not retrying",
            extra={"error": error_message}
        )
        return RetryDecision.DO_NOT_RETRY, None
    
    def detect_error_type(self, error_message: str) -> DBErrorType:
        """
        Detect database error type from error message.
        
        Args:
            error_message: Error message
            
        Returns:
            Detected error type
        """
        error_message_lower = error_message.lower()
        
        # Check for deadlock
        if any(term in error_message_lower for term in [
            "deadlock",
            "serialization failure",
            "could not serialize",
        ]):
            return self.DBErrorType.DEADLOCK
        
        # Check for connection timeout
        if any(term in error_message_lower for term in [
            "connection timeout",
            "connect timeout",
            "timeout while connecting",
        ]):
            return self.DBErrorType.CONNECTION_TIMEOUT
        
        # Check for statement timeout
        if any(term in error_message_lower for term in [
            "statement timeout",
            "query timeout",
            "statement was aborted",
        ]):
            return self.DBErrorType.STATEMENT_TIMEOUT
        
        # Check for constraint violation
        if any(term in error_message_lower for term in [
            "constraint",
            "unique constraint",
            "foreign key constraint",
            "violates",
        ]):
            return self.DBErrorType.CONSTRAINT_VIOLATION
        
        # Check for connection lost
        if any(term in error_message_lower for term in [
            "connection lost",
            "connection closed",
            "server closed the connection",
            "broken pipe",
        ]):
            return self.DBErrorType.CONNECTION_LOST
        
        # Default to unknown
        return self.DBErrorType.UNKNOWN
