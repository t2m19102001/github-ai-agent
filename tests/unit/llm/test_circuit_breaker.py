#!/usr/bin/env python3
"""
Unit tests for Circuit Breaker.
"""

import pytest
import time

from src.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)


class TestCircuitBreaker:
    """Test CircuitBreaker."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        config = CircuitBreakerConfig(failure_threshold=5, timeout_seconds=60)
        breaker = CircuitBreaker("test_provider", config)
        
        assert breaker.provider_name == "test_provider"
        assert breaker.get_state() == CircuitState.CLOSED
    
    def test_record_success(self):
        """Test recording success."""
        breaker = CircuitBreaker("test_provider")
        
        breaker.record_success()
        
        assert breaker._success_count == 1
        assert breaker.get_state() == CircuitState.CLOSED
    
    def test_record_failure(self):
        """Test recording failure."""
        breaker = CircuitBreaker("test_provider", CircuitBreakerConfig(failure_threshold=3))
        
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        
        assert breaker._failure_count == 3
        assert breaker.get_state() == CircuitState.OPEN
    
    def test_circuit_opening(self):
        """Test circuit opening after threshold."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test_provider", config)
        
        breaker.record_failure()
        breaker.record_failure()
        
        assert breaker.get_state() == CircuitState.OPEN
    
    def test_can_execute_closed(self):
        """Test execution allowed when circuit closed."""
        breaker = CircuitBreaker("test_provider")
        
        assert breaker.can_execute() is True
    
    def test_can_execute_open(self):
        """Test execution blocked when circuit open."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test_provider", config)
        
        breaker.record_failure()
        breaker.record_failure()
        
        assert breaker.can_execute() is False
    
    def test_half_open_state(self):
        """Test HALF_OPEN state after timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=1)
        breaker = CircuitBreaker("test_provider", config)
        
        # Open circuit
        breaker.record_failure()
        breaker.record_failure()
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Try to execute (should move to HALF_OPEN)
        breaker.can_execute()
        
        assert breaker.get_state() == CircuitState.HALF_OPEN
    
    def test_circuit_closing(self):
        """Test circuit closing after successes in HALF_OPEN."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=1, success_threshold=2)
        breaker = CircuitBreaker("test_provider", config)
        
        # Open circuit
        breaker.record_failure()
        breaker.record_failure()
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Move to HALF_OPEN
        breaker.can_execute()
        
        # Record successes
        breaker.record_success()
        breaker.record_success()
        
        assert breaker.get_state() == CircuitState.CLOSED
    
    def test_get_stats(self):
        """Test getting circuit breaker stats."""
        breaker = CircuitBreaker("test_provider")
        
        breaker.record_success()
        breaker.record_failure()
        
        stats = breaker.get_stats()
        
        assert stats["provider"] == "test_provider"
        assert stats["failure_count"] == 1
        assert stats["success_count"] == 1
    
    def test_reset(self):
        """Test circuit breaker reset."""
        breaker = CircuitBreaker("test_provider")
        
        breaker.record_failure()
        breaker.record_failure()
        
        breaker.reset()
        
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._success_count == 0
