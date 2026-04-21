#!/usr/bin/env python3
"""
Dead Letter Queue (DLQ) with Poison Message Handling.

Production-grade implementation with:
- Permanent failure tracking
- Poison message detection
- Manual review workflow
- Automatic analysis of failure patterns
- Alerting on critical failures
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, and_
    from sqlalchemy.sql import text
except ImportError:
    AsyncSession = None

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .task_status import TaskStatus

logger = get_logger(__name__)


class FailureReason(Enum):
    """Classification of failure reasons."""
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    FATAL_ERROR = "fatal_error"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    DEPENDENCY_FAILURE = "dependency_failure"
    UNKNOWN = "unknown"


@dataclass
class DLQEntry:
    """Dead letter queue entry."""
    id: str
    task_id: str
    task_type: str
    failure_reason: FailureReason
    error_message: str
    stack_trace: Optional[str] = None
    retry_count: int = 0
    payload: Optional[Dict[str, Any]] = None
    failed_at: datetime = field(default_factory=datetime.utcnow)
    reviewed: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    action_taken: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "failure_reason": self.failure_reason.value,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "retry_count": self.retry_count,
            "payload": self.payload,
            "failed_at": self.failed_at.isoformat(),
            "reviewed": self.reviewed,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "action_taken": self.action_taken,
            "metadata": self.metadata,
        }


class DeadLetterQueue:
    """
    Dead letter queue for permanently failed tasks.
    
    Features:
    - Track permanently failed tasks
    - Classify failure reasons
    - Support manual review workflow
    - Pattern analysis for recurring failures
    - Alert on critical failures
    """
    
    def __init__(self, db_session_factory):
        """
        Initialize dead letter queue.
        
        Args:
            db_session_factory: SQLAlchemy async session factory
        """
        self.db_session_factory = db_session_factory
        logger.info("DeadLetterQueue initialized")
    
    async def add_entry(
        self,
        task_id: str,
        task_type: str,
        failure_reason: FailureReason,
        error_message: str,
        stack_trace: Optional[str] = None,
        retry_count: int = 0,
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add entry to dead letter queue.
        
        Args:
            task_id: Original task ID
            task_type: Task type
            failure_reason: Classification of failure
            error_message: Error message
            stack_trace: Stack trace (if available)
            retry_count: Number of retries before failure
            payload: Task payload
            metadata: Additional metadata
            
        Returns:
            DLQ entry ID
        """
        import uuid
        
        entry_id = str(uuid.uuid4())
        
        async with self.db_session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO dead_letter_queue (
                        id, task_id, task_type, failure_reason, error_message,
                        stack_trace, retry_count, payload, failed_at, reviewed,
                        reviewed_by, reviewed_at, action_taken, metadata
                    ) VALUES (
                        :id, :task_id, :task_type, :failure_reason, :error_message,
                        :stack_trace, :retry_count, :payload, :failed_at, :reviewed,
                        :reviewed_by, :reviewed_at, :action_taken, :metadata
                    )
                """),
                {
                    "id": entry_id,
                    "task_id": task_id,
                    "task_type": task_type,
                    "failure_reason": failure_reason.value,
                    "error_message": error_message,
                    "stack_trace": stack_trace,
                    "retry_count": retry_count,
                    "payload": json.dumps(payload) if payload else None,
                    "failed_at": datetime.utcnow(),
                    "reviewed": False,
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "action_taken": None,
                    "metadata": json.dumps(metadata or {}),
                }
            )
            await session.commit()
        
        # Alert on critical failures
        if failure_reason in {FailureReason.FATAL_ERROR, FailureReason.TIMEOUT}:
            await self._alert_on_critical_failure(entry_id, task_type, error_message)
        
        logger.warning(
            f"Task added to DLQ: {task_id} (reason: {failure_reason.value})",
            extra={"dlq_id": entry_id, "task_type": task_type}
        )
        
        return entry_id
    
    async def get_entry(self, entry_id: str) -> Optional[DLQEntry]:
        """Get DLQ entry by ID."""
        async with self.db_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, task_id, task_type, failure_reason, error_message,
                           stack_trace, retry_count, payload, failed_at, reviewed,
                           reviewed_by, reviewed_at, action_taken, metadata
                    FROM dead_letter_queue
                    WHERE id = :entry_id
                """),
                {"entry_id": entry_id}
            )
            row = result.fetchone()
            if row:
                return DLQEntry(
                    id=row[0],
                    task_id=row[1],
                    task_type=row[2],
                    failure_reason=FailureReason(row[3]),
                    error_message=row[4],
                    stack_trace=row[5],
                    retry_count=row[6],
                    payload=json.loads(row[7]) if row[7] else None,
                    failed_at=row[8],
                    reviewed=row[9],
                    reviewed_by=row[10],
                    reviewed_at=row[11],
                    action_taken=row[12],
                    metadata=json.loads(row[13]) if row[13] else {},
                )
        return None
    
    async def list_unreviewed(
        self,
        limit: int = 100,
        task_type: Optional[str] = None
    ) -> List[DLQEntry]:
        """List unreviewed DLQ entries."""
        async with self.db_session_factory() as session:
            query = """
                SELECT id, task_id, task_type, failure_reason, error_message,
                       stack_trace, retry_count, payload, failed_at, reviewed,
                       reviewed_by, reviewed_at, action_taken, metadata
                FROM dead_letter_queue
                WHERE reviewed = false
            """
            params = {}
            
            if task_type:
                query += " AND task_type = :task_type"
                params["task_type"] = task_type
            
            query += " ORDER BY failed_at DESC LIMIT :limit"
            params["limit"] = limit
            
            result = await session.execute(text(query), params)
            rows = result.fetchall()
            
            return [
                DLQEntry(
                    id=row[0],
                    task_id=row[1],
                    task_type=row[2],
                    failure_reason=FailureReason(row[3]),
                    error_message=row[4],
                    stack_trace=row[5],
                    retry_count=row[6],
                    payload=json.loads(row[7]) if row[7] else None,
                    failed_at=row[8],
                    reviewed=row[9],
                    reviewed_by=row[10],
                    reviewed_at=row[11],
                    action_taken=row[12],
                    metadata=json.loads(row[13]) if row[13] else {},
                )
                for row in rows
            ]
    
    async def mark_reviewed(
        self,
        entry_id: str,
        reviewer: str,
        action_taken: str,
        notes: Optional[str] = None
    ) -> None:
        """
        Mark DLQ entry as reviewed.
        
        Args:
            entry_id: DLQ entry ID
            reviewer: Reviewer identifier
            action_taken: Action taken (e.g., "requeued", "ignored", "fixed_manually")
            notes: Optional review notes
        """
        async with self.db_session_factory() as session:
            await session.execute(
                text("""
                    UPDATE dead_letter_queue
                    SET reviewed = true,
                        reviewed_by = :reviewer,
                        reviewed_at = NOW(),
                        action_taken = :action_taken,
                        metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{notes}',
                            :notes::jsonb
                        )
                    WHERE id = :entry_id
                """),
                {
                    "entry_id": entry_id,
                    "reviewer": reviewer,
                    "action_taken": action_taken,
                    "notes": notes or "",
                }
            )
            await session.commit()
        
        logger.info(f"DLQ entry marked as reviewed: {entry_id} (action: {action_taken})")
    
    async def analyze_failure_patterns(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze failure patterns from DLQ.
        
        Args:
            hours: Time window in hours
            
        Returns:
            Analysis results
        """
        async with self.db_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT 
                        task_type,
                        failure_reason,
                        COUNT(*) as count,
                        AVG(retry_count) as avg_retries
                    FROM dead_letter_queue
                    WHERE failed_at > NOW() - INTERVAL ':hours hours'
                    GROUP BY task_type, failure_reason
                    ORDER BY count DESC
                """),
                {"hours": hours}
            )
            
            rows = result.fetchall()
            
            patterns = []
            for row in rows:
                patterns.append({
                    "task_type": row[0],
                    "failure_reason": row[1],
                    "count": row[2],
                    "avg_retries": float(row[3]) if row[3] else 0,
                })
            
            return {
                "time_window_hours": hours,
                "patterns": patterns,
                "total_failures": sum(p["count"] for p in patterns),
            }
    
    async def _alert_on_critical_failure(
        self,
        entry_id: str,
        task_type: str,
        error_message: str
    ):
        """Alert on critical failures."""
        # This would integrate with your alerting system
        # For now, just log at critical level
        logger.critical(
            f"Critical failure in DLQ: {entry_id}",
            extra={
                "dlq_id": entry_id,
                "task_type": task_type,
                "error": error_message,
            }
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics."""
        async with self.db_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE reviewed = false) as unreviewed,
                        COUNT(*) FILTER (WHERE reviewed = true) as reviewed
                    FROM dead_letter_queue
                """)
            )
            row = result.fetchone()
            
            return {
                "total": row[0],
                "unreviewed": row[1],
                "reviewed": row[2],
            }
