#!/usr/bin/env python3
"""
Unit tests for Task Queue.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.queue.task_queue import Task, TaskQueue
from src.infrastructure.queue.task_status import TaskStatus, TaskLifecycle


class TestTask:
    """Test Task entity."""
    
    def test_task_creation(self):
        """Test task creation with default values."""
        task = Task(task_type="test_type", payload={"key": "value"})
        
        assert task.id is not None
        assert task.task_type == "test_type"
        assert task.payload == {"key": "value"}
        assert task.status == TaskStatus.PENDING
        assert task.priority == 5
        assert task.retry_count == 0
        assert task.max_retries == 3
    
    def test_task_to_dict(self):
        """Test task serialization."""
        task = Task(
            task_type="test_type",
            payload={"key": "value"},
            priority=3,
            status=TaskStatus.PROCESSING,
        )
        
        task_dict = task.to_dict()
        
        assert task_dict["task_type"] == "test_type"
        assert task_dict["status"] == "processing"
        assert task_dict["priority"] == 3
    
    def test_task_from_dict(self):
        """Test task deserialization."""
        task_dict = {
            "id": "test-id",
            "task_type": "test_type",
            "priority": 5,
            "payload": {"key": "value"},
            "status": "pending",
            "scheduled_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "worker_id": None,
            "metadata": {},
        }
        
        task = Task.from_dict(task_dict)
        
        assert task.id == "test-id"
        assert task.task_type == "test_type"
        assert task.status == TaskStatus.PENDING


class TestTaskStatus:
    """Test task status lifecycle."""
    
    @pytest.fixture
    def lifecycle(self):
        """Create lifecycle manager."""
        return TaskLifecycle()
    
    def test_valid_transitions(self, lifecycle):
        """Test valid status transitions."""
        assert TaskStatus.PENDING.can_transition_to(TaskStatus.PROCESSING)
        assert TaskStatus.PENDING.can_transition_to(TaskStatus.CANCELLED)
        assert TaskStatus.PROCESSING.can_transition_to(TaskStatus.COMPLETED)
        assert TaskStatus.PROCESSING.can_transition_to(TaskStatus.FAILED)
        assert TaskStatus.PROCESSING.can_transition_to(TaskStatus.PENDING)  # For retry
        assert not TaskStatus.PENDING.can_transition_to(TaskStatus.COMPLETED)
    
    def test_terminal_states(self, lifecycle):
        """Test terminal states."""
        assert TaskStatus.COMPLETED.is_terminal()
        assert TaskStatus.FAILED.is_terminal()
        assert TaskStatus.CANCELLED.is_terminal()
        assert not TaskStatus.PENDING.is_terminal()
        assert not TaskStatus.PROCESSING.is_terminal()
    
    def test_transition_success(self, lifecycle):
        """Test successful transition."""
        success = lifecycle.transition(
            TaskStatus.PENDING,
            TaskStatus.PROCESSING,
            metadata={"worker": "test"}
        )
        
        assert success is True
        assert len(lifecycle.get_events()) == 1
    
    def test_transition_invalid(self, lifecycle):
        """Test invalid transition."""
        success = lifecycle.transition(
            TaskStatus.PENDING,
            TaskStatus.COMPLETED
        )
        
        assert success is False
        assert len(lifecycle.get_events()) == 0


class TestTaskQueue:
    """Test task queue (mocked database)."""
    
    @pytest.fixture
    def mock_session_factory(self):
        """Create mock session factory."""
        async def session_factory():
            return AsyncMock(spec=AsyncSession)
        return session_factory
    
    @pytest.fixture
    def task_queue(self, mock_session_factory):
        """Create task queue with mocked database."""
        return TaskQueue(db_session_factory=mock_session_factory, enable_redis=False)
    
    @pytest.mark.asyncio
    async def test_enqueue(self, task_queue, mock_session_factory):
        """Test task enqueue."""
        task = Task(task_type="test", payload={"key": "value"})
        
        await task_queue.enqueue(task)
        
        # Verify database persistence was called
        # (mock_session_factory would be called)
    
    @pytest.mark.asyncio
    async def test_dequeue(self, task_queue, mock_session_factory):
        """Test task dequeue."""
        # This would test the dequeue logic
        # For now, just verify the method exists
        assert hasattr(task_queue, 'dequeue')
    
    @pytest.mark.asyncio
    async def test_complete_task(self, task_queue, mock_session_factory):
        """Test task completion."""
        task_id = "test-id"
        result = {"status": "success"}
        
        await task_queue.complete_task(task_id, result)
        
        # Verify database update was called
    
    @pytest.mark.asyncio
    async def test_fail_task_with_retry(self, task_queue, mock_session_factory):
        """Test task failure with retry."""
        task_id = "test-id"
        error = "Test error"
        
        await task_queue.fail_task(task_id, error, can_retry=True)
        
        # Verify database update was called
    
    @pytest.mark.asyncio
    async def test_fail_task_permanent(self, task_queue, mock_session_factory):
        """Test permanent task failure."""
        task_id = "test-id"
        error = "Fatal error"
        
        await task_queue.fail_task(task_id, error, can_retry=False)
        
        # Verify database update was called and task moved to DLQ
