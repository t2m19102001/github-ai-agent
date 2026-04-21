#!/usr/bin/env python3
"""
Unit tests for Tracing.
"""

import pytest

from src.observability.tracing import TraceContext, Tracer, start_trace, end_trace


class TestTraceContext:
    """Test TraceContext."""
    
    def test_trace_context_creation(self):
        """Test trace context creation."""
        context = TraceContext()
        
        assert context.trace_id is not None
        assert context.span_id is not None
        assert context.parent_span_id is None
        assert context.request_id is None
    
    def test_trace_context_with_request_id(self):
        """Test trace context with request ID."""
        context = TraceContext(request_id="req-123")
        
        assert context.request_id == "req-123"
    
    def test_child_span(self):
        """Test child span creation."""
        parent = TraceContext()
        child = parent.child_span()
        
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.span_id != parent.span_id
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        context = TraceContext(request_id="req-123")
        
        context_dict = context.to_dict()
        
        assert context_dict["trace_id"] == context.trace_id
        assert context_dict["span_id"] == context.span_id
        assert context_dict["request_id"] == "req-123"


class TestTracer:
    """Test Tracer."""
    
    def test_tracer_initialization(self):
        """Test tracer initialization."""
        tracer = Tracer()
        
        assert tracer is not None
    
    def test_start_span(self):
        """Test starting a span."""
        tracer = Tracer()
        
        span = tracer.start_span("test_operation")
        
        assert span is not None
        assert span.metadata["operation_name"] == "test_operation"
    
    def test_end_span(self):
        """Test ending a span."""
        tracer = Tracer()
        
        span = tracer.start_span("test_operation")
        tracer.end_span(span)
        
        # Should not raise exception
        assert True
    
    def test_current_span(self):
        """Test getting current span."""
        tracer = Tracer()
        
        span = tracer.start_span("test_operation")
        current = tracer.current_span()
        
        assert current == span
    
    def test_nested_spans(self):
        """Test nested spans."""
        tracer = Tracer()
        
        parent = tracer.start_span("parent")
        child = tracer.start_span("child", parent_span=parent)
        
        assert child.parent_span_id == parent.span_id


class TestTraceFunctions:
    """Test trace utility functions."""
    
    def test_start_trace(self):
        """Test starting a trace."""
        context = start_trace("test_operation", request_id="req-123")
        
        assert context is not None
        assert context.request_id == "req-123"
        assert context.metadata["operation_name"] == "test_operation"
    
    def test_end_trace(self):
        """Test ending a trace."""
        context = start_trace("test_operation")
        
        # Should not raise exception
        end_trace(context)
        assert True
