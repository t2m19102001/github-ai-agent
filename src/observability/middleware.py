#!/usr/bin/env python3
"""
Metrics Middleware for FastAPI.

Production-grade implementation with:
- Request metrics (duration, count)
- Error metrics
- Active request tracking
- Label propagation
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .metrics import BusinessMetrics, Counter, Gauge, Histogram
from .tracing import get_trace_context, set_trace_context, start_trace, end_trace

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Metrics middleware for FastAPI.
    
    Tracks:
    - Request duration
    - Request count
    - Error count
    - Active requests
    """
    
    def __init__(
        self,
        app,
        business_metrics: BusinessMetrics,
        track_request_duration: bool = True,
        track_request_count: bool = True,
        track_errors: bool = True,
    ):
        """
        Initialize metrics middleware.
        
        Args:
            app: ASGI application
            business_metrics: Business metrics instance
            track_request_duration: Track request duration
            track_request_count: Track request count
            track_errors: Track errors
        """
        super().__init__(app)
        self.business_metrics = business_metrics
        self.track_request_duration = track_request_duration
        self.track_request_count = track_request_count
        self.track_errors = track_errors
        
        # Custom metrics
        self.request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration",
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
        )
        self.request_count = Counter(
            "http_requests_total",
            "Total HTTP requests",
            labels={"method": "", "path": "", "status": ""},
        )
        self.request_errors = Counter(
            "http_errors_total",
            "Total HTTP errors",
            labels={"method": "", "path": "", "status": ""},
        )
        self.active_requests = Gauge(
            "http_active_requests",
            "Active HTTP requests",
        )
        
        logger.info("MetricsMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with metrics collection.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response
        """
        # Get or create trace context
        trace_context = get_trace_context()
        if not trace_context:
            trace_context = start_trace(
                operation_name=f"{request.method} {request.url.path}",
                request_id=request.headers.get("X-Request-ID"),
            )
        
        # Increment active requests
        self.active_requests.inc()
        
        # Track start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Track request count
            if self.track_request_count:
                self.request_count.labels(
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                ).inc()
            
            # Track request duration
            if self.track_request_duration:
                self.request_duration.observe(duration)
            
            # Track errors
            if self.track_errors and response.status_code >= 400:
                self.request_errors.labels(
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                ).inc()
            
            # Add metrics headers
            response.headers["X-Request-Duration"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            # Calculate duration even on error
            duration = time.time() - start_time
            
            # Track error
            if self.track_errors:
                self.request_errors.labels(
                    method=request.method,
                    path=request.url.path,
                    status="500",
                ).inc()
            
            # Track duration
            if self.track_request_duration:
                self.request_duration.observe(duration)
            
            logger.error(
                f"Request failed: {e}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration,
                    "trace_id": trace_context.trace_id if trace_context else None,
                }
            )
            
            raise
            
        finally:
            # Decrement active requests
            self.active_requests.dec()
            
            # End trace
            if trace_context:
                end_trace(trace_context)
