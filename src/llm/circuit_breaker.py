#!/usr/bin/env python3
"""
Circuit Breaker for Provider Failover.

Production-grade implementation with:
- State machine (CLOSED, OPEN, HALF_OPEN)
- Failure threshold
- Recovery timeout
- Safe failover logic
"""

import time
import asyncio
import threading
from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker state."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Provider failing, circuit open
    HALF_OPEN = "half_open"  # Testing if provider recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes before closing
    timeout_seconds: int = 60  # Time before trying again (OPEN state)


class CircuitBreaker:
    """
    Circuit breaker for provider failover.
    
    Prevents cascading failures by:
    - Opening circuit after N failures
    - Keeping circuit open for timeout period
    - Testing provider in HALF_OPEN state
    - Closing circuit after N successes
    """
    
    def __init__(
        self,
        provider_name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            provider_name: Name of provider being protected
            config: Circuit breaker configuration
        """
        self.provider_name = provider_name
        self.config = config or CircuitBreakerConfig()
        
        # State - protected by lock for thread safety
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        
        logger.info(
            f"CircuitBreaker initialized for {provider_name} "
            f"(failure_threshold: {self.config.failure_threshold}, "
            f"timeout: {self.config.timeout_seconds}s)"
        )
    
    def record_success(self):
        """Record successful operation."""
        with self._lock:
            self._success_count += 1
            
            if self._state == CircuitState.HALF_OPEN:
                if self._success_count >= self.config.success_threshold:
                    self._close_circuit()
            
            logger.debug(
                f"CircuitBreaker success: {self.provider_name} "
                f"(state: {self._state.value}, success_count: {self._success_count})"
            )
    
    def record_failure(self):
        """Record failed operation."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.config.failure_threshold:
                self._open_circuit()
            
            logger.warning(
                f"CircuitBreaker failure: {self.provider_name} "
                f"(state: {self._state.value}, failure_count: {self._failure_count})"
            )
    
    def _open_circuit(self):
        """Open circuit (provider failing)."""
        if self._state != CircuitState.OPEN:
            old_state = self._state
            self._state = CircuitState.OPEN
            self._opened_at = time.time()
            self._success_count = 0
            
            logger.critical(
                f"Circuit breaker OPENED for {self.provider_name} "
                f"(after {self._failure_count} failures, previous state: {old_state.value})"
            )
    
    def _close_circuit(self):
        """Close circuit (provider recovered)."""
        if self._state != CircuitState.CLOSED:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            
            logger.info(f"Circuit breaker CLOSED for {self.provider_name}")
    
    def _try_half_open(self):
        """Try HALF_OPEN state (testing recovery)."""
        if self._state == CircuitState.OPEN:
            if self._opened_at and (time.time() - self._opened_at) >= self.config.timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                
                logger.info(f"Circuit breaker HALF_OPEN for {self.provider_name}")
    
    def can_execute(self) -> bool:
        """
        Check if operation can execute.
        
        Returns:
            True if circuit allows execution, False otherwise
        """
        with self._lock:
            self._try_half_open()
            
            if self._state == CircuitState.OPEN:
                logger.warning(f"Circuit breaker OPEN, blocking execution: {self.provider_name}")
                return False
            
            return True
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "provider": self.provider_name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time,
                "opened_at": self._opened_at,
            }
    
    def reset(self):
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._opened_at = None
        
        logger.info(f"Circuit breaker reset for {self.provider_name}")
