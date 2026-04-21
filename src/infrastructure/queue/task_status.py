#!/usr/bin/env python3
"""
Task Status Lifecycle Management.

Production-grade implementation with:
- Task status enum with valid transitions
- State machine validation
- Lifecycle tracking
- Event publishing on state changes
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Task status with lifecycle tracking."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    def can_transition_to(self, new_status: 'TaskStatus') -> bool:
        """Check if transition to new status is valid."""
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.PROCESSING, TaskStatus.CANCELLED],
            TaskStatus.PROCESSING: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.PENDING],  # PENDING for retry
            TaskStatus.COMPLETED: [],  # Terminal state
            TaskStatus.FAILED: [TaskStatus.PENDING],  # Can retry
            TaskStatus.CANCELLED: [],  # Terminal state
        }
        return new_status in valid_transitions.get(self, [])
    
    def is_terminal(self) -> bool:
        """Check if status is terminal (no further transitions)."""
        return self in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}


@dataclass
class TaskLifecycleEvent:
    """Task lifecycle event."""
    event_type: str
    from_status: Optional[TaskStatus]
    to_status: TaskStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskLifecycle:
    """
    Task lifecycle manager.
    
    Manages task state transitions with validation and event publishing.
    """
    
    def __init__(self):
        """Initialize task lifecycle manager."""
        self._events: List[TaskLifecycleEvent] = []
        logger.info("TaskLifecycle initialized")
    
    def transition(
        self,
        current_status: TaskStatus,
        new_status: TaskStatus,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Attempt to transition task to new status.
        
        Args:
            current_status: Current task status
            new_status: Desired new status
            metadata: Optional metadata for the transition
            
        Returns:
            True if transition succeeded, False otherwise
        """
        metadata = metadata or {}
        
        # Validate transition
        if not current_status.can_transition_to(new_status):
            logger.warning(
                f"Invalid status transition: {current_status.value} -> {new_status.value}",
                extra={"metadata": metadata}
            )
            return False
        
        # Record event
        event = TaskLifecycleEvent(
            event_type=f"transition_{current_status.value}_to_{new_status.value}",
            from_status=current_status,
            to_status=new_status,
            metadata=metadata,
        )
        self._events.append(event)
        
        logger.info(
            f"Task status transition: {current_status.value} -> {new_status.value}",
            extra={"metadata": metadata}
        )
        
        return True
    
    def get_events(self) -> List[TaskLifecycleEvent]:
        """Get all lifecycle events."""
        return self._events.copy()
    
    def clear_events(self):
        """Clear lifecycle events (for testing or cleanup)."""
        self._events.clear()
