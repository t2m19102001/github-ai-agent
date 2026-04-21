#!/usr/bin/env python3
"""
Distributed Tracing with Trace ID Propagation.

Production-grade implementation with:
- Trace ID generation (UUID v4)
- Span management
- Context propagation
- Request ID support
- Distributed tracing support
"""

import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from contextvars import ContextVar
from datetime import datetime

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


# Context variables for trace propagation
_trace_context: ContextVar[Optional['TraceContext']] = ContextVar('trace_context', default=None)


@dataclass
class TraceContext:
    """
    Distributed tracing context.
    
    Contains trace ID, span ID, and parent span ID for distributed tracing.
    """
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Metadata
    started_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def child_span(self) -> 'TraceContext':
        """Create child span context."""
        return TraceContext(
            trace_id=self.trace_id,
            parent_span_id=self.span_id,
            request_id=self.request_id,
            metadata=self.metadata.copy(),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "request_id": self.request_id,
            "started_at": self.started_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TraceContext':
        """Create from dictionary."""
        return cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            request_id=data.get("request_id"),
            metadata=data.get("metadata", {}),
        )


class Tracer:
    """
    Distributed tracer.
    
    Manages trace context and span lifecycle.
    """
    
    def __init__(self):
        """Initialize tracer."""
        self._current_span: ContextVar[Optional['TraceContext']] = ContextVar(
            'current_span',
            default=None
        )
        logger.info("Tracer initialized")
    
    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[TraceContext] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TraceContext:
        """
        Start a new span.
        
        Args:
            operation_name: Name of the operation being traced
            parent_span: Parent span context (if nested)
            metadata: Additional metadata
            
        Returns:
            TraceContext
        """
        if parent_span:
            span = parent_span.child_span()
        else:
            span = TraceContext(metadata=metadata or {})
        
        span.metadata["operation_name"] = operation_name
        self._current_span.set(span)
        
        logger.debug(
            f"Span started: {operation_name}",
            extra={"trace_id": span.trace_id, "span_id": span.span_id}
        )
        
        return span
    
    def end_span(self, span: TraceContext) -> None:
        """
        End a span.
        
        Args:
            span: Span to end
        """
        duration = (datetime.utcnow() - span.started_at).total_seconds()
        
        logger.debug(
            f"Span ended: {span.metadata.get('operation_name')} "
            f"(duration: {duration:.3f}s)",
            extra={"trace_id": span.trace_id, "span_id": span.span_id}
        )
    
    def current_span(self) -> Optional[TraceContext]:
        """Get current span context."""
        return self._current_span.get()
    
    def get_trace_context(self) -> Optional[TraceContext]:
        """Get current trace context."""
        return _trace_context.get()
    
    def set_trace_context(self, context: TraceContext) -> None:
        """Set trace context."""
        _trace_context.set(context)
    
    def clear_trace_context(self) -> None:
        """Clear trace context."""
        _trace_context.set(None)


# Global tracer instance
tracer = Tracer()


def get_trace_context() -> Optional[TraceContext]:
    """Get current trace context."""
    return tracer.get_trace_context()


def set_trace_context(context: TraceContext) -> None:
    """Set trace context."""
    tracer.set_trace_context(context)


def start_trace(
    operation_name: str,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> TraceContext:
    """
    Start a new trace.
    
    Args:
        operation_name: Name of the operation
        request_id: Request ID (optional)
        metadata: Additional metadata
        
    Returns:
        TraceContext
    """
    context = TraceContext(
        request_id=request_id,
        metadata=metadata or {}
    )
    context.metadata["operation_name"] = operation_name
    
    tracer.set_trace_context(context)
    tracer.start_span(operation_name, context)
    
    return context


def end_trace(context: TraceContext) -> None:
    """
    End a trace.
    
    Args:
        context: Trace context to end
    """
    tracer.end_span(context)
    tracer.clear_trace_context()
