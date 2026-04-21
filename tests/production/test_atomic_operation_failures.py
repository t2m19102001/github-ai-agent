#!/usr/bin/env python3
"""
Failure simulation tests for atomic operations.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from src.workflow.idempotency import IdempotencyManager
from src.llm.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


@pytest.mark.production
class TestAtomicOperationFailures:
    """Test atomic operations under failure conditions."""
    
    @pytest.mark.asyncio
    async def test_atomic_deduplication_redis_connection_failure(self):
        """Test atomic deduplication fails gracefully on Redis connection failure."""
        redis_client = AsyncMock()
        redis_client.set = AsyncMock(side_effect=Exception("Connection refused"))
        redis_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        
        manager = IdempotencyManager(redis_client, ttl_hours=24)
        
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # Should fail open (allow processing)
        is_duplicate, cached = await manager.check_and_mark_atomic(workflow_id, result)
        
        assert is_duplicate is False
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_atomic_deduplication_redis_timeout(self):
        """Test atomic deduplication fails gracefully on Redis timeout."""
        redis_client = AsyncMock()
        redis_client.set = AsyncMock(side_effect=asyncio.TimeoutError("Redis timeout"))
        
        manager = IdempotencyManager(redis_client, ttl_hours=24)
        
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # Should fail open
        is_duplicate, cached = await manager.check_and_mark_atomic(workflow_id, result)
        
        assert is_duplicate is False
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_atomic_deduplication_redis_memory_error(self):
        """Test atomic deduplication fails gracefully on Redis memory error."""
        redis_client = AsyncMock()
        redis_client.set = AsyncMock(side_effect=Exception("OOM command not allowed"))
        
        manager = IdempotencyManager(redis_client, ttl_hours=24)
        
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # Should fail open
        is_duplicate, cached = await manager.check_and_mark_atomic(workflow_id, result)
        
        assert is_duplicate is False
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_atomic_deduplication_concurrent_redis_failures(self):
        """Test concurrent atomic operations with Redis failures."""
        redis_client = AsyncMock()
        failure_count = 0
        
        async def flaky_set(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count % 2 == 0:
                raise Exception("Redis error")
            return True
        
        redis_client.set = flaky_set
        redis_client.get = AsyncMock(return_value=None)
        
        manager = IdempotencyManager(redis_client, ttl_hours=24)
        
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # Concurrent requests
        tasks = [
            manager.check_and_mark_atomic(workflow_id, result)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete (fail open)
        assert all(isinstance(r, tuple) for r in results)
        assert all(len(r) == 2 for r in results)
    
    @pytest.mark.asyncio
    async def test_atomic_deduplication_get_failure_after_set_success(self):
        """Test atomic deduplication handles get failure after set success."""
        redis_client = AsyncMock()
        redis_client.set = AsyncMock(return_value=True)
        redis_client.get = AsyncMock(side_effect=Exception("Redis error"))
        
        manager = IdempotencyManager(redis_client, ttl_hours=24)
        
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # First call should succeed (set works)
        is_duplicate1, cached1 = await manager.check_and_mark_atomic(workflow_id, result)
        assert is_duplicate1 is False
        assert cached1 is None
        
        # Second call (set returns None, but get fails)
        redis_client.set = AsyncMock(return_value=None)
        is_duplicate2, cached2 = await manager.check_and_mark_atomic(workflow_id, result)
        
        # Should still detect duplicate even with get failure
        assert is_duplicate2 is True
        assert cached2 is None
    
    def test_circuit_breaker_concurrent_failures_with_lock(self):
        """Test circuit breaker handles concurrent failures with lock."""
        config = CircuitBreakerConfig(failure_threshold=5, success_threshold=2, timeout_seconds=1)
        breaker = CircuitBreaker("test", config)
        
        num_threads = 10
        num_failures = 10
        
        def record_failures():
            for _ in range(num_failures):
                breaker.record_failure()
        
        threads = [threading.Thread(target=record_failures) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify failure count is correct (no corruption)
        stats = breaker.get_stats()
        expected_failures = num_threads * num_failures
        assert stats["failure_count"] == expected_failures
        
        # Verify circuit opened
        assert breaker.get_state() == CircuitState.OPEN
    
    def test_circuit_breaker_concurrent_state_transitions(self):
        """Test circuit breaker handles concurrent state transitions."""
        config = CircuitBreakerConfig(failure_threshold=3, success_threshold=2, timeout_seconds=1)
        breaker = CircuitBreaker("test", config)
        
        def mixed_operations():
            for i in range(100):
                if i % 2 == 0:
                    breaker.record_failure()
                else:
                    breaker.record_success()
        
        threads = [threading.Thread(target=mixed_operations) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify state is consistent
        stats = breaker.get_stats()
        assert stats["state"] in ["closed", "open", "half_open"]
        assert stats["failure_count"] >= 0
        assert stats["success_count"] >= 0
    
    def test_circuit_breaker_concurrent_can_execute(self):
        """Test circuit breaker can_execute is thread-safe."""
        config = CircuitBreakerConfig(failure_threshold=10, success_threshold=2, timeout_seconds=60)
        breaker = CircuitBreaker("test", config)
        
        results = []
        
        def check_can_execute():
            for _ in range(100):
                results.append(breaker.can_execute())
        
        threads = [threading.Thread(target=check_can_execute) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All results should be booleans
        assert all(isinstance(r, bool) for r in results)
        assert len(results) == 1000
    
    @pytest.mark.asyncio
    async def test_atomic_deduplication_json_serialization_failure(self):
        """Test atomic deduplication handles JSON serialization failure."""
        redis_client = AsyncMock()
        
        # Create unserializable object
        class Unserializable:
            pass
        
        manager = IdempotencyManager(redis_client, ttl_hours=24)
        
        workflow_id = "test-workflow-123"
        result = {"status": "completed", "object": Unserializable()}
        
        # Should fail gracefully
        is_duplicate, cached = await manager.check_and_mark_atomic(workflow_id, result)
        
        assert is_duplicate is False
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_atomic_deduplication_json_deserialization_failure(self):
        """Test atomic deduplication handles JSON deserialization failure."""
        redis_client = AsyncMock()
        redis_client.set = AsyncMock(return_value=None)
        redis_client.get = AsyncMock(return_value="invalid json")
        
        manager = IdempotencyManager(redis_client, ttl_hours=24)
        
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # First call (set succeeds)
        redis_client.set = AsyncMock(return_value=True)
        is_duplicate1, cached1 = await manager.check_and_mark_atomic(workflow_id, result)
        assert is_duplicate1 is False
        
        # Second call (duplicate detected, but get returns invalid JSON)
        redis_client.set = AsyncMock(return_value=None)
        is_duplicate2, cached2 = await manager.check_and_mark_atomic(workflow_id, result)
        
        # Should detect duplicate but return None for cached
        assert is_duplicate2 is True
        assert cached2 is None
    
    @pytest.mark.asyncio
    async def test_atomic_deduplication_concurrent_with_intermittent_failures(self):
        """Test atomic deduplication with intermittent Redis failures."""
        redis_client = AsyncMock()
        call_count = 0
        
        async def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise Exception("Redis error")
            return True if call_count % 2 == 0 else None
        
        redis_client.set = intermittent_failure
        redis_client.get = AsyncMock(return_value='{"status": "completed"}')
        
        manager = IdempotencyManager(redis_client, ttl_hours=24)
        
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # Concurrent requests with intermittent failures
        tasks = [
            manager.check_and_mark_atomic(workflow_id, result)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete (fail open on errors)
        assert all(isinstance(r, tuple) for r in results)


import threading
