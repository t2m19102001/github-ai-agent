#!/usr/bin/env python3
"""
Task Worker with Graceful Restart Support.

Production-grade implementation with:
- FOR UPDATE SKIP LOCKED task claiming
- Timeout handling
- Failure recovery
- Graceful shutdown
- Heartbeat monitoring
"""

import asyncio
import signal
import traceback
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .task_queue import TaskQueue, Task
from .dead_letter_queue import DeadLetterQueue, FailureReason
from .task_status import TaskStatus, TaskLifecycle
from ..retry.retry_policy import RetryPolicy, MaxRetriesExceededError

logger = get_logger(__name__)


class Worker:
    """
    Task worker with graceful restart support.
    
    Features:
    - Claims tasks with FOR UPDATE SKIP LOCKED
    - Handles task execution with timeout
    - Automatic retry with exponential backoff
    - Graceful shutdown on SIGTERM/SIGINT
    - Heartbeat monitoring
    - Failure recovery
    """
    
    def __init__(
        self,
        task_queue: TaskQueue,
        dlq: DeadLetterQueue,
        retry_policy: RetryPolicy,
        worker_id: Optional[str] = None,
        max_concurrent_tasks: int = 5,
        task_timeout: int = 300,  # 5 minutes
        heartbeat_interval: int = 30,
    ):
        """
        Initialize worker.
        
        Args:
            task_queue: Task queue instance
            dlq: Dead letter queue instance
            retry_policy: Retry policy instance
            worker_id: Worker identifier (auto-generated if None)
            max_concurrent_tasks: Maximum concurrent tasks
            task_timeout: Task execution timeout in seconds
            heartbeat_interval: Heartbeat interval in seconds
        """
        self.task_queue = task_queue
        self.dlq = dlq
        self.retry_policy = retry_policy
        self.worker_id = worker_id or f"worker_{datetime.utcnow().timestamp()}"
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout = task_timeout
        self.heartbeat_interval = heartbeat_interval
        
        self._running = False
        self._shutdown_requested = False
        self._concurrent_tasks: Dict[str, asyncio.Task] = {}
        self._task_handlers: Dict[str, Callable] = {}
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        logger.info(
            f"Worker initialized (id: {self.worker_id}, "
            f"max_concurrent: {max_concurrent_tasks}, timeout: {task_timeout}s)"
        )
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self._shutdown_requested = True
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """
        Register handler for specific task type.
        
        Args:
            task_type: Task type to handle
            handler: Async function that takes Task and returns result
        """
        self._task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    async def start(self):
        """Start worker main loop."""
        self._running = True
        logger.info(f"Worker {self.worker_id} starting")
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Start task processing loop
        try:
            while self._running and not self._shutdown_requested:
                await self._process_tasks()
                
                # Wait before next iteration
                await asyncio.sleep(1)
        finally:
            # Cancel heartbeat
            heartbeat_task.cancel()
            
            # Graceful shutdown
            await self._graceful_shutdown()
    
    async def _process_tasks(self):
        """Process tasks from queue."""
        # Check concurrent task limit
        if len(self._concurrent_tasks) >= self.max_concurrent_tasks:
            return
        
        # Get available slots
        available_slots = self.max_concurrent_tasks - len(self._concurrent_tasks)
        
        # Dequeue tasks
        tasks = await self.task_queue.dequeue(
            worker_id=self.worker_id,
            limit=available_slots
        )
        
        for task in tasks:
            # Start task processing
            task_task = asyncio.create_task(self._execute_task(task))
            self._concurrent_tasks[task.id] = task_task
    
    async def _execute_task(self, task: Task):
        """
        Execute task with timeout and error handling.
        
        Args:
            task: Task to execute
        """
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_task_logic(task),
                timeout=self.task_timeout
            )
            
            # Mark as completed
            await self.task_queue.complete_task(task.id, result)
            
        except asyncio.TimeoutError:
            logger.error(f"Task {task.id} timed out after {self.task_timeout}s")
            await self._handle_task_failure(task, "timeout", "Task execution timeout")
            
        except MaxRetriesExceededError as e:
            logger.error(f"Task {task.id} exceeded max retries: {e}")
            await self._handle_task_failure(task, "max_retries", str(e))
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}", exc_info=True)
            
            # Check if should retry
            retry_result = self.retry_policy.should_retry(e, task.retry_count)
            
            if retry_result.should_retry and task.retry_count < task.max_retries:
                # Retry task
                task.retry_count += 1
                await self.task_queue.fail_task(task.id, str(e), can_retry=True)
                
                # Schedule retry with backoff
                await asyncio.sleep(retry_result.delay_seconds)
                await self.task_queue.enqueue(task, delay_seconds=0)
                
            else:
                # Move to DLQ
                await self._handle_task_failure(task, "fatal", str(e), traceback.format_exc())
        
        finally:
            # Remove from concurrent tasks
            self._concurrent_tasks.pop(task.id, None)
    
    async def _execute_task_logic(self, task: Task) -> Dict[str, Any]:
        """
        Execute task logic (delegated to handler).
        
        Args:
            task: Task to execute
            
        Returns:
            Task result
        """
        handler = self._task_handlers.get(task.task_type)
        
        if not handler:
            raise ValueError(f"No handler registered for task type: {task.task_type}")
        
        return await handler(task)
    
    async def _handle_task_failure(
        self,
        task: Task,
        reason: str,
        error_message: str,
        stack_trace: Optional[str] = None
    ):
        """
        Handle task failure (move to DLQ if permanent).
        
        Args:
            task: Failed task
            reason: Failure reason
            error_message: Error message
            stack_trace: Stack trace
        """
        # Determine if should move to DLQ
        if task.retry_count >= task.max_retries:
            failure_reason = FailureReason.MAX_RETRIES_EXCEEDED
        else:
            failure_reason = FailureReason.FATAL_ERROR
        
        await self.dlq.add_entry(
            task_id=task.id,
            task_type=task.task_type,
            failure_reason=failure_reason,
            error_message=error_message,
            stack_trace=stack_trace,
            retry_count=task.retry_count,
            payload=task.payload,
        )
        
        # Mark as failed in queue
        await self.task_queue.fail_task(task.id, error_message, can_retry=False)
    
    async def _heartbeat_loop(self):
        """Heartbeat loop for monitoring."""
        while self._running:
            try:
                # Log heartbeat with stats
                logger.info(
                    f"Worker {self.worker_id} heartbeat",
                    extra={
                        "concurrent_tasks": len(self._concurrent_tasks),
                        "max_concurrent": self.max_concurrent_tasks,
                        "shutdown_requested": self._shutdown_requested,
                    }
                )
                
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _graceful_shutdown(self):
        """
        Graceful shutdown procedure.
        
        1. Stop accepting new tasks
        2. Wait for in-flight tasks to complete (with timeout)
        3. Force-cancel if timeout exceeded
        """
        logger.info(f"Worker {self.worker_id} initiating graceful shutdown")
        
        # Wait for in-flight tasks
        shutdown_timeout = 60  # 1 minute
        start_time = datetime.utcnow()
        
        while self._concurrent_tasks and (datetime.utcnow() - start_time).total_seconds() < shutdown_timeout:
            logger.info(f"Waiting for {len(self._concurrent_tasks)} in-flight tasks")
            await asyncio.sleep(5)
        
        # Cancel remaining tasks
        if self._concurrent_tasks:
            logger.warning(f"Cancelling {len(self._concurrent_tasks)} remaining tasks")
            for task_id, task in self._concurrent_tasks.items():
                task.cancel()
        
        self._running = False
        logger.info(f"Worker {self.worker_id} shutdown complete")
    
    async def stop(self):
        """Request worker shutdown."""
        self._shutdown_requested = True
        logger.info(f"Worker {self.worker_id} shutdown requested")
