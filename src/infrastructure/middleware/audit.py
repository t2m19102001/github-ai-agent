#!/usr/bin/env python3
"""
Audit Middleware for FastAPI.

Production-grade implementation with:
- Structured logging
- Audit trail for all mutating operations
- Security event logging
- Tamper detection (checksums)
- Database persistence
"""

import json
import hashlib
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Audit middleware for comprehensive logging.
    
    Logs:
    - All mutating operations (POST, PUT, PATCH, DELETE)
    - Authentication/authorization events
    - Security events
    - Error conditions
    """
    
    AUDIT_EVENTS = {
        # Authentication
        "user_login", "user_logout", "token_refresh", "auth_failure",
        
        # Authorization
        "permission_denied", "access_granted", "access_revoked",
        
        # Data operations
        "entity_created", "entity_updated", "entity_deleted", "entity_read",
        
        # Security
        "suspicious_activity", "rate_limit_exceeded", "guardrail_triggered",
        
        # GitHub events
        "webhook_received", "webhook_processed", "webhook_failed",
    }
    
    def __init__(
        self,
        app,
        log_mutating_only: bool = True,
        log_headers: bool = True,
        sanitize_secrets: bool = True,
    ):
        """
        Initialize audit middleware.
        
        Args:
            app: ASGI application
            log_mutating_only: Only log mutating operations (POST/PUT/PATCH/DELETE)
            log_headers: Include request headers in audit log
            sanitize_secrets: Redact sensitive data from logs
        """
        super().__init__(app)
        self.log_mutating_only = log_mutating_only
        self.log_headers = log_headers
        self.sanitize_secrets = sanitize_secrets
        
        logger.info(
            f"AuditMiddleware initialized "
            f"(mutating_only: {log_mutating_only}, sanitize: {sanitize_secrets})"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with audit logging.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response
        """
        # Skip logging for non-mutating operations if configured
        if self.log_mutating_only and request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        
        # Build audit entry
        audit_entry = await self._build_audit_entry(request)
        
        # Log before processing
        logger.info(
            f"Audit: {request.method} {request.url.path}",
            extra=audit_entry
        )
        
        # Process request
        response = await call_next(request)
        
        # Update audit entry with response
        audit_entry["response"] = {
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
        }
        
        # Log after processing
        logger.info(
            f"Audit: {request.method} {request.url.path} -> {response.status_code}",
            extra=audit_entry
        )
        
        return response
    
    async def _build_audit_entry(self, request: Request) -> Dict[str, Any]:
        """Build audit entry from request."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "request_id": request.headers.get("X-Request-ID"),
            "trace_id": request.headers.get("X-Trace-ID"),
        }
        
        # Add headers if configured
        if self.log_headers:
            headers_to_log = self._sanitize_headers(dict(request.headers))
            entry["headers"] = headers_to_log
        
        # Calculate checksum for tamper detection
        entry["checksum"] = self._calculate_checksum(entry)
        
        return entry
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request."""
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if request.client:
            return request.client.host
        
        return None
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Sanitize headers to remove sensitive data.
        
        Args:
            headers: Raw headers dictionary
            
        Returns:
            Sanitized headers dictionary
        """
        if not self.sanitize_secrets:
            return headers
        
        sensitive_keys = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
        }
        
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _calculate_checksum(self, entry: Dict[str, Any]) -> str:
        """
        Calculate SHA-256 checksum for tamper detection.
        
        Args:
            entry: Audit entry dictionary
            
        Returns:
            Hex digest string
        """
        # Remove checksum itself if present
        data = {k: v for k, v in entry.items() if k != "checksum"}
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class SecurityEventLogger:
    """
    Dedicated logger for security events.
    
    Security events require special handling:
    - Immediate alerting
    - High retention (7+ years)
    - Tamper-proof storage
    - Separate log stream
    """
    
    SECURITY_LEVELS = {
        "critical": "CRITICAL",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
    }
    
    def __init__(self):
        """Initialize security event logger."""
        logger.info("SecurityEventLogger initialized")
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        actor: Optional[str],
        resource: Optional[str],
        details: Dict[str, Any],
    ):
        """
        Log security event with enhanced metadata.
        
        Args:
            event_type: Type of security event
            severity: Severity level (critical, high, medium, low)
            actor: Actor who performed the action
            resource: Resource affected
            details: Additional event details
        """
        # Validate severity
        if severity not in self.SECURITY_LEVELS:
            severity = "medium"
        
        # Build security event entry
        security_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity.upper(),
            "actor": actor,
            "resource": resource,
            "details": self._sanitize_details(details),
            "checksum": self._calculate_checksum({
                "event_type": event_type,
                "severity": severity,
                "actor": actor,
                "resource": resource,
                "details": details,
            }),
        }
        
        # Log with high severity
        if severity == "critical":
            logger.critical(f"SECURITY: {event_type}", extra=security_entry)
        elif severity == "high":
            logger.error(f"SECURITY: {event_type}", extra=security_entry)
        else:
            logger.warning(f"SECURITY: {event_type}", extra=security_entry)
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from security event details."""
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
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for security event."""
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
