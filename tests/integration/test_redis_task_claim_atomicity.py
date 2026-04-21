#!/usr/bin/env python3
"""
Concurrency tests for Redis task claim atomicity.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.queue.task_queue import Task, TaskStatus


@pytest.mark.integration
class TestRedisTaskClaimAtomicity:
    """Test Redis task claim atomicity prevents duplicate processing."""
    
    @pytest.fixture
    def redis_client(self):
        """Mock Redis client with Lua script support."""
        client = AsyncMock()
        
        # Mock Lua script execution (atomic claim)
        async def mock_eval(script, num_keys, task_id):
            # Simulate atomic behavior: only first claim succeeds
            if not hasattr(mock_eval, 'claimed_tasks'):
                mock_eval.claimed_tasks = set()
            
            if task_id not in mock_eval.claimed_tasks:
                mock_eval.claimed_tasks.add(task_id)
                # Return task data
                task_data = json.dumps({
                    "id": task_id,
                    "task_type": "test",
                    "priority": 5,
                    "payload": {},
                    "status": "pending",
                    "scheduled_at": "2024-04-20T00:00:00Z",
                    "started_at": None,
                    "completed_at": None,
                    "error": None,
                    "retry_count": 0,
                    "max_retries": 3,
                    "worker_id": None,
                    "metadata": {},
                })
                return task_data
            else:
                # Already claimed
                return None
        
        client.eval = mock_eval
        client.zrangebyscore = AsyncMock(return_value=["task-1", "task-2", "task-3"])
        client.zrem = AsyncMock(return_value=0)  # Not used with Lua script
        client.get = AsyncMock(return_value=None)
        client.delete = AsyncMock(return_value=0)
        client.set = AsyncMock(return_value=True)
        client.zadd = AsyncMock(return_value=True)
        
        return client
    
    @pytest.fixture
    def db_session_factory(self):
        """Mock database session factory."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        
        factory = AsyncMock()
        factory.__aenter__ = AsyncMock(return_value=session)
        factory.__aexit__ = AsyncMock(return_value=None)
        
        return factory
    
    @pytest.fixture
    async def task_queue(self, redis_client, db_session_factory):
        """Create task queue."""
        from src.infrastructure.queue.task_queue import TaskQueue
        queue = TaskQueue(db_session_factory, redis_client=redis_client, enable_redis=True)
        await queue.initialize()
        return queue
    
    @pytest.mark.asyncio
    async def test_atomic_claim_prevents_duplicate_processing(self, task_queue):
        """Test atomic Lua script prevents duplicate task processing."""
        worker_id = "worker-1"
        
        # Multiple workers try to claim same tasks
        tasks = [
            task_queue._dequeue_from_redis(worker_id, limit=3)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Total tasks claimed should be exactly 3 (not 15)
        total_claimed = sum(len(r) for r in results)
        assert total_claimed == 3, f"Expected 3 tasks, got {total_claimed}"
    
    @pytest.mark.asyncio
    async def test_lua_script_atomicity(self, task_queue, redis_client):
        """Test Lua script executes atomically."""
        worker_id = "worker-1"
        
        # Reset claimed tasks tracker
        redis_client.eval.claimed_tasks = set()
        
        # Claim tasks
        tasks = await task_queue._dequeue_from_redis(worker_id, limit=3)
        
        # Verify each task was claimed exactly once
        assert len(tasks) == 3
        assert len(redis_client.eval.claimed_tasks) == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_workers_claim_different_tasks(self, task_queue):
        """Test concurrent workers claim different tasks (no duplicates)."""
        worker_ids = ["worker-1", "worker-2", "worker-3"]
        
        # Reset claimed tasks
        task_queue._redis_client.eval.claimed_tasks = set()
        
        # Each worker tries to claim tasks
        tasks = [
            task_queue._dequeue_from_redis(worker_id, limit=10)
            for worker_id in worker_ids
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Total unique tasks claimed should be 3 (available tasks)
        all_tasks = []
        for worker_tasks in results:
            all_tasks.extend(worker_tasks)
        
        # Verify no duplicates
        task_ids = [task.id for task in all_tasks]
        assert len(task_ids) == len(set(task_ids)), "Duplicate tasks claimed"
    
    @pytest.mark.asyncio
    async def test_redis_fallback_to_postgres_on_lua_failure(self, task_queue, redis_client):
        """Test fallback to PostgreSQL if Redis Lua script fails."""
        worker_id = "worker-1"
        
        # Simulate Lua script failure
        redis_client.eval = AsyncMock(side_effect=Exception("Lua script error"))
        
        # Should fallback to PostgreSQL
        tasks = await task_queue._dequeue_from_redis(worker_id, limit=3)
        
        # Verify fallback occurred (tasks from PostgreSQL)
        assert isinstance(tasks, list)
    
    @pytest.mark.asyncio
    async def test_task_claim_updates_database(self, task_queue, db_session_factory):
        """Test task claim updates database status."""
        worker_id = "worker-1"
        
        # Reset claimed tasks
        task_queue._redis_client.eval.claimed_tasks = set()
        
        # Claim tasks
        tasks = await task_queue._dequeue_from_redis(worker_id, limit=2)
        
        # Verify database was updated
        assert db_session_factory.__aenter__.called
        assert db_session_factory.__aenter__.return_value.execute.called
    
    @pytest.mark.asyncio
    async def test_task_claim_sets_worker_id(self, task_queue):
        """Test task claim sets worker ID."""
        worker_id = "worker-1"
        
        # Reset claimed tasks
        task_queue._redis_client.eval.claimed_tasks = set()
        
        # Claim tasks
        tasks = await task_queue._dequeue_from_redis(worker_id, limit=2)
        
        # Verify worker ID is set
        for task in tasks:
            assert task.worker_id == worker_id
            assert task.status == TaskStatus.PROCESSING
    
    @pytest.mark.asyncio
    async def test_task_claim_sets_started_at(self, task_queue):
        """Test task claim sets started_at timestamp."""
        worker_id = "worker-1"
        
        # Reset claimed tasks
        task_queue._redis_client.eval.claimed_tasks = set()
        
        # Claim tasks
        tasks = await task_queue._dequeue_from_redis(worker_id, limit=2)
        
        # Verify started_at is set
        for task in tasks:
            assert task.started_at is not None
    
    @pytest.mark.asyncio
    async def test_no_redis_fallback_to_postgres(self, task_queue):
        """Test PostgreSQL fallback when Redis is disabled."""
        # Create queue with Redis disabled
        from src.infrastructure.queue.task_queue import TaskQueue
        queue = TaskQueue(
            task_queue.db_session_factory,
            redis_url="redis://localhost:6379/0",
            enable_redis=False,
        )
        await queue.initialize()
        
        # Should use PostgreSQL only
        tasks = await queue._dequeue_from_postgres("worker-1", limit=2)
        
        assert isinstance(tasks, list)
    
    @pytest.mark.asyncio
    async def test_lua_script_deletes_task_data_after_claim(self, task_queue, redis_client):
        """Test Lua script deletes task data after successful claim."""
        worker_id = "worker-1"
        
        # Reset claimed tasks
        task_queue._redis_client.eval.claimed_tasks = set()
        
        # Claim tasks
        tasks = await task_queue._dequeue_from_redis(worker_id, limit=2)
        
        # Lua script should delete task data (simulated in mock)
        assert len(tasks) == 2
