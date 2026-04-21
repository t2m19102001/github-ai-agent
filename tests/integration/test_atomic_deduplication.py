#!/usr/bin/env python3
"""
Integration tests for atomic deduplication.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from src.workflow.idempotency import IdempotencyManager


@pytest.mark.integration
class TestAtomicDeduplication:
    """Test atomic deduplication with Redis."""
    
    @pytest.fixture
    async def redis_client(self):
        """Mock Redis client."""
        client = AsyncMock()
        client.set = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.exists = AsyncMock(return_value=0)
        return client
    
    @pytest.fixture
    def idempotency_manager(self, redis_client):
        """Create idempotency manager."""
        return IdempotencyManager(redis_client, ttl_hours=24)
    
    @pytest.mark.asyncio
    async def test_atomic_check_and_mark_first_call(self, idempotency_manager, redis_client):
        """Test first call marks as processed atomically."""
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        is_duplicate, cached = await idempotency_manager.check_and_mark_atomic(
            workflow_id, result
        )
        
        assert is_duplicate is False
        assert cached is None
        assert redis_client.set.called
        assert redis_client.set.call_args[1]["nx"] is True
    
    @pytest.mark.asyncio
    async def test_atomic_check_and_mark_duplicate(self, idempotency_manager, redis_client):
        """Test duplicate call is detected atomically."""
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # First call sets the key
        redis_client.set = AsyncMock(return_value=True)
        is_duplicate1, _ = await idempotency_manager.check_and_mark_atomic(workflow_id, result)
        assert is_duplicate1 is False
        
        # Second call detects duplicate (set returns None)
        redis_client.set = AsyncMock(return_value=None)
        redis_client.get = AsyncMock(return_value='{"status": "completed"}')
        is_duplicate2, cached = await idempotency_manager.check_and_mark_atomic(workflow_id, result)
        
        assert is_duplicate2 is True
        assert cached == {"status": "completed"}
    
    @pytest.mark.asyncio
    async def test_concurrent_atomic_operations(self, idempotency_manager, redis_client):
        """Test concurrent atomic operations prevent race condition."""
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # Simulate 10 concurrent requests
        tasks = [
            idempotency_manager.check_and_mark_atomic(workflow_id, result)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)
        
        # Only first should succeed (is_duplicate=False)
        # All others should be duplicates (is_duplicate=True)
        duplicate_count = sum(1 for is_dup, _ in results if is_dup)
        success_count = sum(1 for is_dup, _ in results if not is_dup)
        
        assert success_count == 1
        assert duplicate_count == 9
    
    @pytest.mark.asyncio
    async def test_atomic_fails_gracefully_on_redis_error(self, idempotency_manager, redis_client):
        """Test atomic operation fails gracefully on Redis error."""
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        # Simulate Redis error
        redis_client.set = AsyncMock(side_effect=Exception("Redis connection error"))
        
        is_duplicate, cached = await idempotency_manager.check_and_mark_atomic(
            workflow_id, result
        )
        
        # Should fail open (allow processing)
        assert is_duplicate is False
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_atomic_with_none_result(self, idempotency_manager, redis_client):
        """Test atomic operation with None result."""
        workflow_id = "test-workflow-123"
        
        redis_client.set = AsyncMock(return_value=True)
        is_duplicate, cached = await idempotency_manager.check_and_mark_atomic(
            workflow_id, None
        )
        
        assert is_duplicate is False
        assert cached is None
        assert redis_client.set.called
    
    @pytest.mark.asyncio
    async def test_atomic_preserves_result_data(self, idempotency_manager, redis_client):
        """Test atomic operation preserves result data."""
        workflow_id = "test-workflow-123"
        result = {
            "status": "completed",
            "timestamp": "2024-04-20T00:00:00Z",
            "metadata": {"key": "value"},
        }
        
        redis_client.set = AsyncMock(return_value=True)
        is_duplicate, cached = await idempotency_manager.check_and_mark_atomic(
            workflow_id, result
        )
        
        assert is_duplicate is False
        # Verify result was serialized correctly
        import json
        stored_value = redis_client.set.call_args[0][1]
        assert json.loads(stored_value) == result
    
    @pytest.mark.asyncio
    async def test_atomic_ttl_set_correctly(self, idempotency_manager, redis_client):
        """Test atomic operation sets TTL correctly."""
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        redis_client.set = AsyncMock(return_value=True)
        await idempotency_manager.check_and_mark_atomic(workflow_id, result)
        
        # Verify TTL is set (24 hours = 86400 seconds)
        assert redis_client.set.call_args[1]["ex"] == 86400
    
    @pytest.mark.asyncio
    async def test_deprecated_is_duplicate_still_works(self, idempotency_manager, redis_client):
        """Test deprecated is_duplicate method still works."""
        workflow_id = "test-workflow-123"
        
        redis_client.exists = AsyncMock(return_value=0)
        is_duplicate = await idempotency_manager.is_duplicate(workflow_id)
        
        assert is_duplicate is False
        assert redis_client.exists.called
    
    @pytest.mark.asyncio
    async def test_deprecated_mark_processed_still_works(self, idempotency_manager, redis_client):
        """Test deprecated mark_processed method still works."""
        workflow_id = "test-workflow-123"
        result = {"status": "completed"}
        
        redis_client.setex = AsyncMock(return_value=True)
        await idempotency_manager.mark_processed(workflow_id, result)
        
        assert redis_client.setex.called
    
    @pytest.mark.asyncio
    async def test_atomic_get_result_cached(self, idempotency_manager, redis_client):
        """Test atomic operation returns cached result on duplicate."""
        workflow_id = "test-workflow-123"
        result = {"status": "completed", "data": "test"}
        
        # First call
        redis_client.set = AsyncMock(return_value=True)
        is_duplicate1, cached1 = await idempotency_manager.check_and_mark_atomic(workflow_id, result)
        assert is_duplicate1 is False
        assert cached1 is None
        
        # Second call (duplicate)
        redis_client.set = AsyncMock(return_value=None)
        redis_client.get = AsyncMock(return_value='{"status": "completed", "data": "test"}')
        is_duplicate2, cached2 = await idempotency_manager.check_and_mark_atomic(workflow_id, result)
        
        assert is_duplicate2 is True
        assert cached2 == {"status": "completed", "data": "test"}
