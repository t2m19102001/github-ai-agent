#!/usr/bin/env python3
"""
Thread safety tests for Circuit Breaker.
"""

import pytest
import threading
import time
import concurrent.futures

from src.llm.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig


@pytest.mark.unit
class TestCircuitBreakerThreadSafety:
    """Test circuit breaker thread safety."""
    
    @pytest.fixture
    def breaker(self):
        """Create circuit breaker with low thresholds for testing."""
        config = CircuitBreakerConfig(failure_threshold=10, success_threshold=3, timeout_seconds=1)
        return CircuitBreaker("test_provider", config)
    
    def test_concurrent_failure_recording(self, breaker):
        """Test concurrent failure recording doesn't corrupt state."""
        num_threads = 50
        num_failures_per_thread = 10
        
        def record_failures():
            for _ in range(num_failures_per_thread):
                breaker.record_failure()
        
        # Launch threads concurrently
        threads = [threading.Thread(target=record_failures) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify failure count is correct (should be num_threads * num_failures_per_thread)
        expected_failures = num_threads * num_failures_per_thread
        actual_failures = breaker.get_stats()["failure_count"]
        
        assert actual_failures == expected_failures, \
            f"Expected {expected_failures} failures, got {actual_failures}"
    
    def test_concurrent_success_recording(self, breaker):
        """Test concurrent success recording doesn't corrupt state."""
        num_threads = 50
        num_successes_per_thread = 10
        
        # Open circuit first
        for _ in range(10):
            breaker.record_failure()
        assert breaker.get_state() == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(1.1)
        
        def record_successes():
            for _ in range(num_successes_per_thread):
                breaker.record_success()
        
        # Launch threads concurrently
        threads = [threading.Thread(target=record_successes) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify success count is correct
        expected_successes = num_threads * num_successes_per_thread
        actual_successes = breaker.get_stats()["success_count"]
        
        assert actual_successes == expected_successes, \
            f"Expected {expected_successes} successes, got {actual_successes}"
    
    def test_concurrent_state_transitions(self, breaker):
        """Test concurrent state transitions are safe."""
        num_threads = 20
        num_operations = 100
        
        def mixed_operations():
            for i in range(num_operations):
                if i % 2 == 0:
                    breaker.record_failure()
                else:
                    breaker.record_success()
        
        # Launch threads concurrently
        threads = [threading.Thread(target=mixed_operations) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify state is consistent
        stats = breaker.get_stats()
        assert stats["state"] in ["closed", "open", "half_open"]
        assert stats["failure_count"] >= 0
        assert stats["success_count"] >= 0
    
    def test_concurrent_can_execute_calls(self, breaker):
        """Test concurrent can_execute calls are thread-safe."""
        num_threads = 50
        num_calls = 100
        results = []
        
        def check_can_execute():
            for _ in range(num_calls):
                result = breaker.can_execute()
                results.append(result)
        
        # Launch threads concurrently
        threads = [threading.Thread(target=check_can_execute) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify all calls returned boolean
        assert all(isinstance(r, bool) for r in results)
        assert len(results) == num_threads * num_calls
    
    def test_concurrent_get_stats_calls(self, breaker):
        """Test concurrent get_stats calls are thread-safe."""
        num_threads = 50
        num_calls = 100
        results = []
        
        def get_stats():
            for _ in range(num_calls):
                stats = breaker.get_stats()
                results.append(stats)
        
        # Launch threads concurrently
        threads = [threading.Thread(target=get_stats) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify all stats are consistent
        assert all(isinstance(r, dict) for r in results)
        assert all("state" in r for r in results)
        assert all("failure_count" in r for r in results)
    
    def test_concurrent_reset(self, breaker):
        """Test concurrent reset operations are safe."""
        # Add some state
        for _ in range(5):
            breaker.record_failure()
        
        num_threads = 10
        
        def reset_breaker():
            breaker.reset()
        
        # Launch threads concurrently
        threads = [threading.Thread(target=reset_breaker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify state is reset
        stats = breaker.get_stats()
        assert stats["failure_count"] == 0
        assert stats["success_count"] == 0
        assert stats["state"] == "closed"
    
    def test_concurrent_failure_and_success(self, breaker):
        """Test concurrent failure and success recording."""
        num_threads = 20
        
        def record_failures():
            for _ in range(10):
                breaker.record_failure()
        
        def record_successes():
            for _ in range(10):
                breaker.record_success()
        
        # Launch mixed threads
        threads = []
        for i in range(num_threads):
            if i % 2 == 0:
                threads.append(threading.Thread(target=record_failures))
            else:
                threads.append(threading.Thread(target=record_successes))
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify state is consistent
        stats = breaker.get_stats()
        assert stats["failure_count"] >= 0
        assert stats["success_count"] >= 0
    
    def test_circuit_opens_exactly_at_threshold(self, breaker):
        """Test circuit opens exactly at threshold, not before."""
        config = CircuitBreakerConfig(failure_threshold=5, success_threshold=2, timeout_seconds=60)
        breaker = CircuitBreaker("test", config)
        
        # Record failures up to threshold - 1
        for _ in range(4):
            breaker.record_failure()
        assert breaker.get_state() == CircuitState.CLOSED
        
        # Record one more failure
        breaker.record_failure()
        assert breaker.get_state() == CircuitState.OPEN
