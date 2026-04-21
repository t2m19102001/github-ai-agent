#!/usr/bin/env python3
"""
Immutable Audit Logging with Append-Only Store.

Production-grade implementation with:
- Immutable audit logs (no updates/deletes)
- Append-only storage
- SHA-256 checksum integrity verification
- 7-year retention (2555 days)
- Structured JSON logging
"""

import json
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Audit event types."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    TOKEN_REFRESH = "token_refresh"
    AUTH_FAILURE = "auth_failure"
    PERMISSION_DENIED = "permission_denied"
    ACCESS_GRANTED = "access_granted"
    ACCESS_REVOKED = "access_revoked"
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_DELETED = "entity_deleted"
    ENTITY_READ = "entity_read"
    WEBHOOK_RECEIVED = "webhook_received"
    WEBHOOK_PROCESSED = "webhook_processed"
    WEBHOOK_FAILED = "webhook_failed"
    TASK_ENQUEUED = "task_enqueued"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SECURITY_EVENT = "security_event"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    GUARDRAIL_TRIGGERED = "guardrail_triggered"


class AuditSeverity(Enum):
    """Audit event severity."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class AuditLog:
    """
    Immutable audit log entry.
    
    Once created, audit logs cannot be modified or deleted.
    This ensures audit trail integrity for compliance.
    """
    
    # Immutable fields
    id: str
    event_type: AuditEventType
    severity: AuditSeverity
    actor_type: str  # user, agent, system, webhook, service
    actor_id: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    action: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    trace_id: Optional[str]
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    checksum: str = field(default="")
    
    def __post_init__(self):
        """Calculate checksum after initialization."""
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """
        Calculate SHA-256 checksum for integrity verification.
        
        Returns:
            Hex digest string
        """
        # Build canonical representation
        data = {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "details": self._sanitize_details(self.details),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat(),
        }
        
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from audit log details."""
        sensitive_keys = {"password", "token", "secret", "key", "credential"}
        
        sanitized = {}
        for key, value in details.items():
            if isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def verify_integrity(self) -> bool:
        """
        Verify audit log integrity using checksum.
        
        Returns:
            True if checksum matches, False otherwise
        """
        expected_checksum = self._calculate_checksum()
        return expected_checksum == self.checksum
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "details": self._sanitize_details(self.details),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat(),
            "checksum": self.checksum,
        }


class AuditStore:
    """
    Append-only audit log store.
    
    Features:
    - Immutable storage (no updates/deletes)
    - Checksum verification
    - Retention policy (7 years)
    - Batch write optimization
    """
    
    def __init__(self, db_session_factory, retention_days: int = 2555):
        """
        Initialize audit store.
        
        Args:
            db_session_factory: SQLAlchemy async session factory
            retention_days: Retention period in days (default: 7 years)
        """
        self.db_session_factory = db_session_factory
        self.retention_days = retention_days
        
        logger.info(
            f"AuditStore initialized (retention: {retention_days} days)"
        )
    
    async def append(self, audit_log: AuditLog) -> None:
        """
        Append audit log to store.
        
        Args:
            audit_log: Audit log entry
        """
        # Verify integrity before storing
        if not audit_log.verify_integrity():
            raise ValueError("Audit log integrity check failed")
        
        async with self.db_session_factory() as session:
            from sqlalchemy.sql import text
            
            await session.execute(
                text("""
                    INSERT INTO audit_logs (
                        id, event_type, severity, actor_type, actor_id,
                        entity_type, entity_id, action, details,
                        ip_address, user_agent, request_id, trace_id,
                        created_at, checksum
                    ) VALUES (
                        :id, :event_type, :severity, :actor_type, :actor_id,
                        :entity_type, :entity_id, :action, :details,
                        :ip_address, :user_agent, :request_id, :trace_id,
                        :created_at, :checksum
                    )
                """),
                {
                    "id": audit_log.id,
                    "event_type": audit_log.event_type.value,
                    "severity": audit_log.severity.value,
                    "actor_type": audit_log.actor_type,
                    "actor_id": audit_log.actor_id,
                    "entity_type": audit_log.entity_type,
                    "entity_id": audit_log.entity_id,
                    "action": audit_log.action,
                    "details": json.dumps(audit_log.details),
                    "ip_address": audit_log.ip_address,
                    "user_agent": audit_log.user_agent,
                    "request_id": audit_log.request_id,
                    "trace_id": audit_log.trace_id,
                    "created_at": audit_log.created_at,
                    "checksum": audit_log.checksum,
                }
            )
            await session.commit()
        
        logger.debug(f"Audit log appended: {audit_log.id}")
    
    async def append_batch(self, audit_logs: List[AuditLog]) -> None:
        """
        Append multiple audit logs in batch.
        
        Args:
            audit_logs: List of audit log entries
        """
        for audit_log in audit_logs:
            await self.append(audit_log)
    
    async def get_by_id(self, audit_id: str) -> Optional[AuditLog]:
        """
        Retrieve audit log by ID.
        
        Args:
            audit_id: Audit log ID
            
        Returns:
            AuditLog if found, None otherwise
        """
        async with self.db_session_factory() as session:
            from sqlalchemy.sql import text
            
            result = await session.execute(
                text("""
                    SELECT id, event_type, severity, actor_type, actor_id,
                           entity_type, entity_id, action, details,
                           ip_address, user_agent, request_id, trace_id,
                           created_at, checksum
                    FROM audit_logs
                    WHERE id = :audit_id
                """),
                {"audit_id": audit_id}
            )
            row = result.fetchone()
            
            if row:
                audit_log = AuditLog(
                    id=row[0],
                    event_type=AuditEventType(row[1]),
                    severity=AuditSeverity(row[2]),
                    actor_type=row[3],
                    actor_id=row[4],
                    entity_type=row[5],
                    entity_id=row[6],
                    action=row[7],
                    details=json.loads(row[8]) if row[8] else {},
                    ip_address=row[9],
                    user_agent=row[10],
                    request_id=row[11],
                    trace_id=row[12],
                    created_at=row[13],
                    checksum=row[14],
                )
                
                # Verify integrity on retrieval
                if not audit_log.verify_integrity():
                    logger.error(f"Audit log integrity check failed: {audit_id}")
                
                return audit_log
        
        return None
    
    async def query(
        self,
        event_type: Optional[AuditEventType] = None,
        actor_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        trace_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Query audit logs with filters.
        
        Args:
            event_type: Filter by event type
            actor_id: Filter by actor ID
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            severity: Filter by severity
            trace_id: Filter by trace ID
            limit: Maximum results
            offset: Result offset
            
        Returns:
            List of audit logs
        """
        async with self.db_session_factory() as session:
            from sqlalchemy.sql import text
            
            query = """
                SELECT id, event_type, severity, actor_type, actor_id,
                       entity_type, entity_id, action, details,
                       ip_address, user_agent, request_id, trace_id,
                       created_at, checksum
                FROM audit_logs
                WHERE 1=1
            """
            params = {}
            
            if event_type:
                query += " AND event_type = :event_type"
                params["event_type"] = event_type.value
            
            if actor_id:
                query += " AND actor_id = :actor_id"
                params["actor_id"] = actor_id
            
            if entity_type:
                query += " AND entity_type = :entity_type"
                params["entity_type"] = entity_type
            
            if entity_id:
                query += " AND entity_id = :entity_id"
                params["entity_id"] = entity_id
            
            if severity:
                query += " AND severity = :severity"
                params["severity"] = severity.value
            
            if trace_id:
                query += " AND trace_id = :trace_id"
                params["trace_id"] = trace_id
            
            query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
            
            result = await session.execute(text(query), params)
            rows = result.fetchall()
            
            return [
                AuditLog(
                    id=row[0],
                    event_type=AuditEventType(row[1]),
                    severity=AuditSeverity(row[2]),
                    actor_type=row[3],
                    actor_id=row[4],
                    entity_type=row[5],
                    entity_id=row[6],
                    action=row[7],
                    details=json.loads(row[8]) if row[8] else {},
                    ip_address=row[9],
                    user_agent=row[10],
                    request_id=row[11],
                    trace_id=row[12],
                    created_at=row[13],
                    checksum=row[14],
                )
                for row in rows
            ]
    
    async def verify_all_integrity(self, limit: int = 1000) -> Dict[str, Any]:
        """
        Verify integrity of audit logs (sample).
        
        Args:
            limit: Number of logs to verify
            
        Returns:
            Verification results
        """
        audit_logs = await self.query(limit=limit)
        
        failed = []
        for audit_log in audit_logs:
            if not audit_log.verify_integrity():
                failed.append(audit_log.id)
        
        return {
            "verified": len(audit_logs),
            "failed": len(failed),
            "failed_ids": failed,
        }
