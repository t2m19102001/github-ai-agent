#!/usr/bin/env python3
"""
Security Event Logger.

Production-grade implementation with:
- Security event classification
- High-retention storage (7+ years)
- Tamper-proof logging
- Immediate alerting
- Compliance-ready
"""

import json
import hashlib
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .audit import AuditLog, AuditEventType, AuditSeverity

logger = get_logger(__name__)


class SecurityEventType(Enum):
    """Security event types."""
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHORIZATION_FAILURE = "authorization_failure"
    PERMISSION_DENIED = "permission_denied"
    DATA_ACCESS_VIOLATION = "data_access_violation"
    DATA_MODIFICATION_VIOLATION = "data_modification_violation"
    INJECTION_ATTEMPT = "injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    CSRF_ATTEMPT = "csrf_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    MALICIOUS_INPUT = "malicious_input"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    CONFIGURATION_CHANGE = "configuration_change"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class SecurityEventLogger:
    """
    Security event logger.
    
    Logs security events with enhanced retention and alerting.
    """
    
    def __init__(self, audit_store):
        """
        Initialize security event logger.
        
        Args:
            audit_store: Audit store instance
        """
        self.audit_store = audit_store
        
        logger.info("SecurityEventLogger initialized")
    
    def log_security_event(
        self,
        event_type: SecurityEventType,
        severity: AuditSeverity,
        actor_type: str,
        actor_id: str,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Log security event.
        
        Args:
            event_type: Security event type
            severity: Event severity
            actor_type: Actor type (user, agent, system)
            actor_id: Actor identifier
            resource: Resource affected
            details: Additional event details
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Request ID
            trace_id: Trace ID
        """
        import uuid
        
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            event_type=AuditEventType.SECURITY_EVENT,
            severity=severity,
            actor_type=actor_type,
            actor_id=actor_id,
            entity_type="security_event",
            entity_id=None,
            action=event_type.value,
            details={
                "security_event_type": event_type.value,
                "resource": resource,
                **(details or {})
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            trace_id=trace_id,
        )
        
        # Store audit log
        import asyncio
        asyncio.create_task(self.audit_store.append(audit_log))
        
        # Alert on critical security events
        if severity in {AuditSeverity.CRITICAL, AuditSeverity.HIGH}:
            logger.critical(
                f"SECURITY EVENT: {event_type.value}",
                extra={
                    "security_event_type": event_type.value,
                    "actor_type": actor_type,
                    "actor_id": actor_id,
                    "resource": resource,
                    "ip_address": ip_address,
                }
            )
        else:
            logger.warning(
                f"SECURITY EVENT: {event_type.value}",
                extra={
                    "security_event_type": event_type.value,
                    "actor_type": actor_type,
                    "actor_id": actor_id,
                }
            )
    
    def log_authentication_failure(
        self,
        username: str,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """
        Log authentication failure.
        
        Args:
            username: Username attempted
            reason: Failure reason
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Request ID
        """
        self.log_security_event(
            event_type=SecurityEventType.AUTHENTICATION_FAILURE,
            severity=AuditSeverity.HIGH,
            actor_type="user",
            actor_id=username,
            resource="authentication",
            details={"reason": reason},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
    
    def log_permission_denied(
        self,
        actor_type: str,
        actor_id: str,
        resource: str,
        action: str,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """
        Log permission denied event.
        
        Args:
            actor_type: Actor type
            actor_id: Actor identifier
            resource: Resource accessed
            action: Action attempted
            ip_address: Client IP address
            request_id: Request ID
        """
        self.log_security_event(
            event_type=SecurityEventType.PERMISSION_DENIED,
            severity=AuditSeverity.MEDIUM,
            actor_type=actor_type,
            actor_id=actor_id,
            resource=resource,
            details={"action": action},
            ip_address=ip_address,
            request_id=request_id,
        )
    
    def log_rate_limit_exceeded(
        self,
        actor_type: str,
        actor_id: str,
        limit: int,
        window_seconds: int,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """
        Log rate limit exceeded event.
        
        Args:
            actor_type: Actor type
            actor_id: Actor identifier
            limit: Rate limit
            window_seconds: Time window
            ip_address: Client IP address
            request_id: Request ID
        """
        self.log_security_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.MEDIUM,
            actor_type=actor_type,
            actor_id=actor_id,
            resource="rate_limit",
            details={
                "limit": limit,
                "window_seconds": window_seconds,
            },
            ip_address=ip_address,
            request_id=request_id,
        )
