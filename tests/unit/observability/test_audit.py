#!/usr/bin/env python3
"""
Unit tests for Audit Log.
"""

import pytest
import json
import hashlib
from datetime import datetime

from src.observability.audit import AuditLog, AuditEventType, AuditSeverity, AuditStore


class TestAuditLog:
    """Test AuditLog entity."""
    
    def test_audit_log_creation(self):
        """Test audit log creation."""
        audit_log = AuditLog(
            id="test-id",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.INFO,
            actor_type="user",
            actor_id="user-123",
            entity_type="session",
            entity_id="session-456",
            action="login",
            details={"ip": "192.168.1.1"},
        )
        
        assert audit_log.id == "test-id"
        assert audit_log.event_type == AuditEventType.USER_LOGIN
        assert audit_log.severity == AuditSeverity.INFO
        assert audit_log.actor_type == "user"
        assert audit_log.actor_id == "user-123"
    
    def test_checksum_calculation(self):
        """Test checksum calculation."""
        audit_log = AuditLog(
            id="test-id",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.INFO,
            actor_type="user",
            actor_id="user-123",
            details={"key": "value"},
        )
        
        assert audit_log.checksum is not None
        assert len(audit_log.checksum) == 64  # SHA-256 hex digest
    
    def test_checksum_verification(self):
        """Test checksum verification."""
        audit_log = AuditLog(
            id="test-id",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.INFO,
            actor_type="user",
            actor_id="user-123",
            details={"key": "value"},
        )
        
        assert audit_log.verify_integrity() is True
    
    def test_checksum_verification_tampered(self):
        """Test checksum verification with tampered data."""
        audit_log = AuditLog(
            id="test-id",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.INFO,
            actor_type="user",
            actor_id="user-123",
            details={"key": "value"},
        )
        
        # Tamper with data
        audit_log.details["key"] = "tampered"
        
        assert audit_log.verify_integrity() is False
    
    def test_sanitize_details(self):
        """Test detail sanitization."""
        audit_log = AuditLog(
            id="test-id",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.INFO,
            actor_type="user",
            actor_id="user-123",
            details={
                "password": "secret123",
                "token": "abc123",
                "safe_field": "safe_value",
            },
        )
        
        serialized = audit_log.to_dict()
        
        assert serialized["details"]["password"] == "[REDACTED]"
        assert serialized["details"]["token"] == "[REDACTED]"
        assert serialized["details"]["safe_field"] == "safe_value"
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        audit_log = AuditLog(
            id="test-id",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.INFO,
            actor_type="user",
            actor_id="user-123",
            details={"key": "value"},
        )
        
        audit_dict = audit_log.to_dict()
        
        assert audit_dict["id"] == "test-id"
        assert audit_dict["event_type"] == "user_login"
        assert audit_dict["severity"] == "INFO"
        assert audit_dict["actor_type"] == "user"
        assert audit_dict["actor_id"] == "user-123"
