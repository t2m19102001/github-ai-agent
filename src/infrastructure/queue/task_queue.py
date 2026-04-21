#!/usr/bin/env python3
"""
Persistent Task Queue with PostgreSQL (Source of Truth) and Redis (Fast Access).

Production-grade implementation with:
- PostgreSQL as durable storage (source of truth)
- Redis as fast-access queue layer
- Automatic fallback to database when Redis unavailable
- Task prioritization
- Delayed task scheduling
"""

import asyncio
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy import select, and_, or_
    from sqlalchemy.sql import text
except ImportError:
    AsyncSession = None

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .task_status import TaskStatus, TaskLifecycle

logger = get_logger(__name__)


@dataclass
class Task:
    """Task entity."""
    id: str = field(default_factory=lambda: str(uuid4()))
    task_type: str = ""
    priority: int = 5  # 1=highest, 10=lowest
    payload: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    worker_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "task_type": self.task_type,
            "priority": self.priority,
            "payload": self.payload,
            "status": self.status.value,
            "scheduled_at": self.scheduled_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "worker_id": self.worker_id,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            task_type=data["task_type"],
            priority=data["priority"],
            payload=data["payload"],
            status=TaskStatus(data["status"]),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            worker_id=data.get("worker_id"),
            metadata=data.get("metadata", {}),
        )


class TaskQueue:
    """
    Persistent task queue with PostgreSQL (source of truth) and Redis (fast access).
    
    Architecture:
    1. PostgreSQL is the durable storage (source of truth)
    2. Redis is a fast-access queue layer
    3. Workers can operate with Redis only for performance
    4. Fallback to PostgreSQL when Redis unavailable
    5. Tasks are written to both Redis and PostgreSQL on enqueue
    6. Workers claim tasks with FOR UPDATE SKIP LOCKED (PostgreSQL)
    """
    
    def __init__(
        self,
        db_session_factory,
        redis_url: str = "redis://localhost:6379/0",
        enable_redis: bool = True,
    ):
        """
        Initialize task queue.
        
        Args:
            db_session_factory: SQLAlchemy async session factory
            redis_url: Redis connection string
            enable_redis: Enable Redis fast-access layer
        """
        self.db_session_factory = db_session_factory
        self.redis_url = redis_url
        self.enable_redis = enable_redis
        self._redis_client: Optional[redis.Redis] = None
        self._lifecycle = TaskLifecycle()
        
        logger.info(
            f"TaskQueue initialized (redis_enabled: {enable_redis}, redis_url: {redis_url})"
        )
    
    async def initialize(self):
        """Initialize connections."""
        if self.enable_redis and redis is not None:
            try:
                self._redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._redis_client.ping()
                logger.info("Redis connection established for task queue")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._redis_client = None
        else:
            logger.warning("Redis disabled or not available, using PostgreSQL only")
    
    async def enqueue(
        self,
        task: Task,
        delay_seconds: int = 0
    ) -> None:
        """
        Enqueue task.
        
        Args:
            task: Task to enqueue
            delay_seconds: Delay before task becomes available
        """
        # Update scheduled time if delayed
        if delay_seconds > 0:
            task.scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        
        # Persist to PostgreSQL (source of truth)
        await self._persist_task(task)
        
        # Add to Redis (fast access)
        if self._redis_client:
            await self._enqueue_to_redis(task)
        
        logger.info(f"Task enqueued: {task.id} (type: {task.task_type}, delay: {delay_seconds}s)")
    
    async def _persist_task(self, task: Task) -> None:
        """Persist task to PostgreSQL."""
        async with self.db_session_factory() as session:
            # Check if task already exists
            existing = await session.execute(
                select(text("SELECT id FROM tasks WHERE id = :task_id")),
                {"task_id": task.id}
            )
            if existing.scalar_one_or_none():
                # Update existing task
                await session.execute(
                    text("""
                        UPDATE tasks
                        SET status = :status,
                        scheduled_at = :scheduled_at,
                        error = :error,
                        retry_count = :retry_count,
                        worker_id = :worker_id
                        WHERE id = :task_id
                    """),
                    {
                        "task_id": task.id,
                        "status": task.status.value,
                        "scheduled_at": task.scheduled_at,
                        "error": task.error,
                        "retry_count": task.retry_count,
                        "worker_id": task.worker_id,
                    }
                )
            else:
                # Insert new task
                await session.execute(
                    text("""
                        INSERT INTO tasks (
                            id, task_type, priority, payload, status,
                            scheduled_at, started_at, completed_at, error,
                            retry_count, max_retries, worker_id, metadata
                        ) VALUES (
                            :id, :task_type, :priority, :payload, :status,
                            :scheduled_at, :started_at, :completed_at, :error,
                            :retry_count, :max_retries, :worker_id, :metadata
                        )
                    """),
                    {
                        "id": task.id,
                        "task_type": task.task_type,
                        "priority": task.priority,
                        "payload": json.dumps(task.payload),
                        "status": task.status.value,
                        "scheduled_at": task.scheduled_at,
                        "started_at": task.started_at,
                        "completed_at": task.completed_at,
                        "error": task.error,
                        "retry_count": task.retry_count,
                        "max_retries": task.max_retries,
                        "worker_id": task.worker_id,
                        "metadata": json.dumps(task.metadata),
                    }
                )
            await session.commit()
    
    async def _enqueue_to_redis(self, task: Task) -> None:
        """Add task to Redis queue."""
        if not self._redis_client:
            return
        
        # Use sorted set for priority scheduling
        score = task.priority + (task.scheduled_at.timestamp() if task.scheduled_at else 0)
        
        await self._redis_client.zadd(
            "task_queue",
            {task.id: score}
        )
        
        # Set task data
        await self._redis_client.set(
            f"task_data:{task.id}",
            json.dumps(task.to_dict()),
            ex=86400  # 24h TTL
        )
    
    async def dequeue(self, worker_id: str, limit: int = 1) -> List[Task]:
        """
        Dequeue tasks for processing.
        
        Uses PostgreSQL FOR UPDATE SKIP LOCKED for safe concurrent access.
        
        Args:
            worker_id: Worker identifier
            limit: Maximum number of tasks to dequeue
            
        Returns:
            List of tasks
        """
        # Try Redis first for performance
        if self._redis_client:
            tasks = await self._dequeue_from_redis(worker_id, limit)
            if tasks:
                return tasks
        
        # Fallback to PostgreSQL
        return await self._dequeue_from_postgres(worker_id, limit)
    
    async def _dequeue_from_redis(self, worker_id: str, limit: int) -> List[Task]:
        """Dequeue from Redis (fast path) with atomic claim."""
        now = datetime.utcnow().timestamp()
        
        # Atomic Lua script to claim task: zrem + get + delete in one operation
        claim_script = """
            local task_id = ARGV[1]
            local removed = redis.call('zrem', 'task_queue', task_id)
            if removed == 1 then
                local task_data = redis.call('get', 'task_data:' .. task_id)
                redis.call('del', 'task_data:' .. task_id)
                return task_data
            end
            return nil
        """
        
        # Get task IDs with score <= now (scheduled tasks ready)
        task_ids = await self._redis_client.zrangebyscore(
            "task_queue",
            min=0,
            max=now,
            start=0,
            num=limit
        )
        
        tasks = []
        for task_id in task_ids:
            # Atomically claim task using Lua script
            task_data = await self._redis_client.eval(
                claim_script,
                0,  # No keys, only arguments
                task_id
            )
            
            if task_data:
                task = Task.from_dict(json.loads(task_data))
                task.status = TaskStatus.PROCESSING
                task.worker_id = worker_id
                task.started_at = datetime.utcnow()
                
                # Update in database
                await self._update_task_status(task)
                
                tasks.append(task)
        
        return tasks
    
    async def _dequeue_from_postgres(self, worker_id: str, limit: int) -> List[Task]:
        """
        Dequeue from PostgreSQL with FOR UPDATE SKIP LOCKED.
        
        This is the source of truth and ensures no race conditions.
        """
        async with self.db_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, task_type, priority, payload, status,
                           scheduled_at, started_at, completed_at, error,
                           retry_count, max_retries, worker_id, metadata
                    FROM tasks
                    WHERE status = 'pending'
                      AND scheduled_at <= NOW()
                    ORDER BY priority ASC, scheduled_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            
            rows = result.fetchall()
            tasks = []
            
            for row in rows:
                task = Task(
                    id=row[0],
                    task_type=row[1],
                    priority=row[2],
                    payload=json.loads(row[3]),
                    status=TaskStatus(row[4]),
                    scheduled_at=row[5],
                    started_at=row[6],
                    completed_at=row[7],
                    error=row[8],
                    retry_count=row[9],
                    max_retries=row[10],
                    worker_id=row[11],
                    metadata=json.loads(row[12]) if row[12] else {},
                )
                
                # Mark as processing
                task.status = TaskStatus.PROCESSING
                task.worker_id = worker_id
                task.started_at = datetime.utcnow()
                
                # Update in database
                await session.execute(
                    text("""
                        UPDATE tasks
                        SET status = :status,
                            worker_id = :worker_id,
                            started_at = :started_at
                        WHERE id = :task_id
                    """),
                    {
                        "task_id": task.id,
                        "status": task.status.value,
                        "worker_id": task.worker_id,
                        "started_at": task.started_at,
                    }
                )
                
                tasks.append(task)
            
            await session.commit()
            return tasks
    
    async def _update_task_status(self, task: Task) -> None:
        """Update task status in PostgreSQL."""
        async with self.db_session_factory() as session:
            await session.execute(
                text("""
                    UPDATE tasks
                    SET status = :status,
                        worker_id = :worker_id,
                        started_at = :started_at
                    WHERE id = :task_id
                """),
                {
                    "task_id": task.id,
                    "status": task.status.value,
                    "worker_id": task.worker_id,
                    "started_at": task.started_at,
                }
            )
            await session.commit()
    
    async def complete_task(self, task_id: str, result: Dict[str, Any]) -> None:
        """Mark task as completed."""
        async with self.db_session_factory() as session:
            await session.execute(
                text("""
                    UPDATE tasks
                    SET status = 'completed',
                        completed_at = NOW(),
                        result = :result
                    WHERE id = :task_id
                """),
                {"task_id": task_id, "result": json.dumps(result)}
            )
            await session.commit()
        
        # Remove from Redis
        if self._redis_client:
            await self._redis_client.zrem("task_queue", task_id)
            await self._redis_client.delete(f"task_data:{task_id}")
        
        logger.info(f"Task completed: {task_id}")
    
    async def fail_task(
        self,
        task_id: str,
        error: str,
        can_retry: bool = True
    ) -> None:
        """
        Mark task as failed.
        
        Args:
            task_id: Task ID
            error: Error message
            can_retry: Whether task can be retried
        """
        async with self.db_session_factory() as session:
            # First, get current retry count
            result = await session.execute(
                text("SELECT retry_count, max_retries FROM tasks WHERE id = :task_id"),
                {"task_id": task_id}
            )
            row = result.fetchone()
            
            if not row:
                logger.warning(f"Task not found for failure handling: {task_id}")
                return
            
            retry_count, max_retries = row[0], row[1]
            
            # Check if we've exceeded max retries (poison message detection)
            if can_retry and retry_count >= max_retries:
                logger.error(f"Task {task_id} exceeded max retries ({max_retries}), sending to DLQ")
                can_retry = False
            
            if can_retry:
                # Calculate exponential backoff delay
                backoff_delay = min(2 ** retry_count, 300)  # Max 5 minutes
                next_scheduled = datetime.utcnow() + timedelta(seconds=backoff_delay)
                
                # Reset to pending for retry with backoff
                await session.execute(
                    text("""
                        UPDATE tasks
                        SET status = 'pending',
                            error = :error,
                            retry_count = retry_count + 1,
                            scheduled_at = :scheduled_at,
                            worker_id = NULL,
                            started_at = NULL
                        WHERE id = :task_id
                    """),
                    {
                        "task_id": task_id, 
                        "error": error,
                        "scheduled_at": next_scheduled
                    }
                )
                logger.info(f"Task {task_id} scheduled for retry {retry_count + 1}/{max_retries} in {backoff_delay}s")
            else:
                # Move to dead letter queue
                await session.execute(
                    text("""
                        INSERT INTO dead_letter_queue (
                            task_id, error, failed_at, retry_count
                        ) VALUES (
                            :task_id, :error, NOW(), :retry_count
                        )
                    """),
                    {"task_id": task_id, "error": error, "retry_count": retry_count}
                )
                
                # Mark as failed permanently
                await session.execute(
                    text("""
                        UPDATE tasks
                        SET status = 'failed',
                            error = :error,
                            completed_at = NOW()
                        WHERE id = :task_id
                    """),
                    {"task_id": task_id, "error": error}
                )
                
                # Alert on poison message
                logger.critical(f"Poison message detected: task_id={task_id}, error={error}, retries={retry_count}")
            
            await session.commit()
        
        # Remove from Redis if failed permanently
        if not can_retry and self._redis_client:
            await self._redis_client.zrem("task_queue", task_id)
            await self._redis_client.delete(f"task_data:{task_id}")
        
        logger.info(f"Task failed: {task_id} (can_retry: {can_retry})")
    
    async def get_queue_depth(self) -> int:
        """Get current queue depth."""
        async with self.db_session_factory() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
            )
            return result.scalar()
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        async with self.db_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, task_type, priority, payload, status,
                           scheduled_at, started_at, completed_at, error,
                           retry_count, max_retries, worker_id, metadata
                    FROM tasks
                    WHERE id = :task_id
                """),
                {"task_id": task_id}
            )
            row = result.fetchone()
            if row:
                return Task(
                    id=row[0],
                    task_type=row[1],
                    priority=row[2],
                    payload=json.loads(row[3]),
                    status=TaskStatus(row[4]),
                    scheduled_at=row[5],
                    started_at=row[6],
                    completed_at=row[7],
                    error=row[8],
                    retry_count=row[9],
                    max_retries=row[10],
                    worker_id=row[11],
                    metadata=json.loads(row[12]) if row[12] else {},
                )
        return None
