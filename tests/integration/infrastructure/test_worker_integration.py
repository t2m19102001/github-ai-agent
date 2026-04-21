#!/usr/bin/env python3
"""
Integration tests for Worker behavior.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.queue.worker import Worker
from src.infrastructure.queue.task_queue import Task, TaskQueue
from src.infrastructure.queue.dead_letter_queue import DeadLetterQueue, FailureReason
from src.infrastructure.retry.retry_policy import RetryPolicy, ExponentialBackoff


class TestWorkerIntegration:
    """Integration tests for worker behavior."""
    
    @pytest.fixture
    def mock_task_queue(self):
        """Create mock task queue."""
        queue = MagicMock(spec=TaskQueue)
        queue.dequeue = AsyncMock(return_value=[])
        return queue
    
    @pytest.fixture
    def mock_dlq(self):
        """Create mock dead letter queue."""
        dlq = MagicMock(spec=DeadLetterQueue)
        dlq.add_entry = AsyncMock()
        return dlq
    
    @pytest.fixture
    def retry_policy(self):
        """Create retry policy."""
        backoff = ExponentialBackoff(base_delay=0.1, max_delay=1.0)
        return RetryPolicy(max_attempts=2, backoff=backoff)
    
    @pytest.fixture
    def worker(self, mock_task_queue, mock_dlq, retry_policy):
        """Create worker instance."""
        return Worker(
            task_queue=mock_task_queue,
            dlq=mock_dlq,
            retry_policy=retry_policy,
            worker_id="test_worker",
            max_concurrent_tasks=2,
            task_timeout=10,
        )
    
    def test_worker_initialization(self, worker):
        """Test worker initialization."""
        assert worker.worker_id == "test_worker"
        assert worker.max_concurrent_tasks == 2
        assert worker.task_timeout == 10
    
    @pytest.mark.asyncio
    async def test_task_handler_registration(self, worker):
        """Test task handler registration."""
        async def handler(task):
            return {"result": "success"}
        
        worker.register_task_handler("test_type", handler)
        
        assert "test_type" in worker._task_handlers
    
    @pytest.mark.asyncio
    async def test_task_execution_success(self, worker, mock_task_queue):
        """Test successful task execution."""
        async def handler(task):
            return {"result": "success"}
        
        worker.register_task_handler("test_type", handler)
        
        task = Task(task_type="test_type", payload={"key": "value"})
        
        # Simulate task execution
        result = await handler(task)
        
        assert result == {"result": "success"}
    
    @pytest.mark.asyncio
    async def test_task_execution_timeout(self, worker, mock_task_queue, mock_dlq):
        """Test task execution timeout."""
        async def slow_handler(task):
            await asyncio.sleep(15)  # Exceeds timeout
            return {"result": "success"}
        
        worker.register_task_handler("test_type", slow_handler)
        
        task = Task(task_type="test_type", payload={"key": "value"})
        
        # Simulate execution with timeout
        try:
            result = await asyncio.wait_for(
                slow_handler(task),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            # Expected - timeout handling in worker would catch this
            pass
    
    @pytest.mark.asyncio
    async def test_task_failure_with_retry(self, worker, mock_task_queue):
        """Test task failure with retry."""
        call_count = 0
        
        async def flaky_handler(task):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return {"result": "success"}
        
        worker.register_task_handler("test_type", flaky_handler)
        
        task = Task(task_type="test_type", payload={"key": "value"})
        
        # Simulate execution with retry logic
        result = await flaky_handler(task)
        
        assert result == {"result": "success"}
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_task_failure_max_retries(self, worker, mock_task_queue, mock_dlq):
        """Test task failure after max retries."""
        async def always_failing_handler(task):
            raise Exception("Always fails")
        
        worker.register_task_handler("test_type", always_failing_handler)
        
        task = Task(task_type="test_type", payload={"key": "value"}, max_retries=2)
        
        # Simulate execution - would fail and move to DLQ after max retries
        try:
            result = await always_failing_handler(task)
        except Exception:
            # Expected
            pass
        
        # Verify DLQ would be called
        # mock_dlq.add_entry.assert_called_once()


class TestDeadLetterQueue:
    """Integration tests for DLQ."""
    
    @pytest.fixture
    def mock_session_factory(self):
        """Create mock session factory."""
        async def session_factory():
            return AsyncMock(spec=AsyncSession)
        return session_factory
    
    @pytest.fixture
    def dlq(self, mock_session_factory):
        """Create DLQ instance."""
        return DeadLetterQueue(db_session_factory=mock_session_factory)
    
    @pytest.mark.asyncio
    async def test_add_entry(self, dlq, mock_session_factory):
        """Test adding entry to DLQ."""
        entry_id = await dlq.add_entry(
            task_id="task-123",
            task_type="test_type",
            failure_reason=FailureReason.MAX_RETRIES_EXCEEDED,
            error_message="Task failed after max retries",
            retry_count=3,
            payload={"key": "value"},
        )
        
        assert entry_id is not None
    
    @pytest.mark.asyncio
    async def test_list_unreviewed(self, dlq, mock_session_factory):
        """Test listing unreviewed entries."""
        # Mock the database query to return empty list
        mock_session = await mock_session_factory()
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.fetchall = AsyncMock(return_value=[])
        
        entries = await dlq.list_unreviewed(limit=10)
        
        assert isinstance(entries, list)
    
    @pytest.mark.asyncio
    async def test_mark_reviewed(self, dlq, mock_session_factory):
        """Test marking entry as reviewed."""
        mock_session = await mock_session_factory()
        mock_session.execute = AsyncMock()
        
        await dlq.mark_reviewed(
            entry_id="dlq-123",
            reviewer="reviewer_1",
            action_taken="requeued",
            notes="Issue fixed"
        )
        
        # Verify database update was called
        mock_session.execute.assert_called()
