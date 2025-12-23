#!/usr/bin/env python3
"""
Performance Metrics and Monitoring for GitHub AI Agent
Implements Prometheus metrics and performance tracking
"""

import time
import json
from typing import Dict, Any, List
from dataclasses import dataclass, field
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Try to import prometheus_client, fallback to simple implementation
try:
    import prometheus_client as prom
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus client not available, using simple metrics")


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    loop_times: List[float] = field(default_factory=list)
    query_times: List[float] = field(default_factory=list)
    webhook_times: List[float] = field(default_factory=list)
    pipeline_times: List[float] = field(default_factory=list)
    success_rates: Dict[str, float] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)
    total_operations: int = 0
    successful_operations: int = 0


class MetricsCollector:
    """Central metrics collection and tracking"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        
        # Prometheus metrics if available
        if PROMETHEUS_AVAILABLE:
            self._setup_prometheus_metrics()
        else:
            self._setup_simple_metrics()
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        self.loop_time_histogram = prom.Histogram(
            'agent_loop_time_seconds',
            'Time per agent role execution',
            ['role'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        self.webhook_latency = prom.Histogram(
            'webhook_processing_seconds',
            'Webhook processing latency',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        self.pipeline_duration = prom.Histogram(
            'autonomous_pipeline_seconds',
            'Autonomous pipeline execution time',
            buckets=[5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
        )
        
        self.success_rate = prom.Gauge(
            'task_success_rate',
            'Task success rate by type',
            ['task_type']
        )
        
        self.error_counter = prom.Counter(
            'error_total',
            'Total errors by type',
            ['error_type', 'component']
        )
        
        self.rag_query_time = prom.Histogram(
            'rag_query_duration_seconds',
            'RAG query processing time',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        logger.info("Prometheus metrics initialized")
    
    def _setup_simple_metrics(self):
        """Setup simple metrics fallback"""
        self.simple_metrics = {
            'loop_times': [],
            'webhook_times': [],
            'pipeline_times': [],
            'rag_times': [],
            'success_rates': {},
            'error_counts': {}
        }
        logger.info("Simple metrics initialized")
    
    def record_loop_time(self, role: str, duration: float):
        """Record agent loop time"""
        self.metrics.loop_times.append(duration)
        
        # Success metric: <5s per role
        if duration > 5.0:
            logger.warning(f"Agent {role} exceeded 5s: {duration:.2f}s")
        
        if PROMETHEUS_AVAILABLE:
            self.loop_time_histogram.labels(role=role).observe(duration)
        else:
            self.simple_metrics['loop_times'].append(duration)
    
    def record_webhook_latency(self, duration: float):
        """Record webhook processing time"""
        self.metrics.webhook_times.append(duration)
        
        # Success metric: <2s latency
        if duration > 2.0:
            logger.warning(f"Webhook processing exceeded 2s: {duration:.2f}s")
        
        if PROMETHEUS_AVAILABLE:
            self.webhook_latency.observe(duration)
        else:
            self.simple_metrics['webhook_times'].append(duration)
    
    def record_pipeline_time(self, duration: float):
        """Record autonomous pipeline time"""
        self.metrics.pipeline_times.append(duration)
        
        if PROMETHEUS_AVAILABLE:
            self.pipeline_duration.observe(duration)
        else:
            self.simple_metrics['pipeline_times'].append(duration)
    
    def record_rag_query_time(self, duration: float):
        """Record RAG query time"""
        self.metrics.query_times.append(duration)
        
        # Success metric: <0.8s retrieval
        if duration > 0.8:
            logger.warning(f"RAG query exceeded 0.8s: {duration:.2f}s")
        
        if PROMETHEUS_AVAILABLE:
            self.rag_query_time.observe(duration)
        else:
            self.simple_metrics['rag_times'].append(duration)
    
    def update_success_rate(self, task_type: str, rate: float):
        """Update success rate metric"""
        self.metrics.success_rates[task_type] = rate
        
        # Success metric thresholds
        if task_type in ['pr_creation', 'autonomous_task'] and rate < 0.9:
            logger.warning(f"Success rate for {task_type} below 90%: {rate:.2%}")
        
        if PROMETHEUS_AVAILABLE:
            self.success_rate.labels(task_type=task_type).set(rate)
        else:
            self.simple_metrics['success_rates'][task_type] = rate
    
    def record_error(self, error_type: str, component: str):
        """Record error occurrence"""
        if error_type not in self.metrics.error_counts:
            self.metrics.error_counts[error_type] = 0
        self.metrics.error_counts[error_type] += 1
        
        if PROMETHEUS_AVAILABLE:
            self.error_counter.labels(error_type=error_type, component=component).inc()
        else:
            if component not in self.simple_metrics['error_counts']:
                self.simple_metrics['error_counts'][component] = {}
            if error_type not in self.simple_metrics['error_counts'][component]:
                self.simple_metrics['error_counts'][component][error_type] = 0
            self.simple_metrics['error_counts'][component][error_type] += 1
    
    def record_operation(self, success: bool):
        """Record general operation success/failure"""
        self.metrics.total_operations += 1
        if success:
            self.metrics.successful_operations += 1
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        # Calculate averages
        avg_loop_time = sum(self.metrics.loop_times) / len(self.metrics.loop_times) if self.metrics.loop_times else 0
        avg_webhook_time = sum(self.metrics.webhook_times) / len(self.metrics.webhook_times) if self.metrics.webhook_times else 0
        avg_pipeline_time = sum(self.metrics.pipeline_times) / len(self.metrics.pipeline_times) if self.metrics.pipeline_times else 0
        avg_rag_time = sum(self.metrics.query_times) / len(self.metrics.query_times) if self.metrics.query_times else 0
        
        # Calculate overall success rate
        overall_success_rate = self.metrics.successful_operations / self.metrics.total_operations if self.metrics.total_operations > 0 else 0
        
        return {
            "agent_performance": {
                "avg_loop_time": avg_loop_time,
                "meets_time_target": avg_loop_time < 5.0,
                "total_loops": len(self.metrics.loop_times)
            },
            "webhook_performance": {
                "avg_latency": avg_webhook_time,
                "meets_latency_target": avg_webhook_time < 2.0,
                "total_webhooks": len(self.metrics.webhook_times)
            },
            "pipeline_performance": {
                "avg_duration": avg_pipeline_time,
                "total_pipelines": len(self.metrics.pipeline_times)
            },
            "rag_performance": {
                "avg_query_time": avg_rag_time,
                "meets_time_target": avg_rag_time < 0.8,
                "total_queries": len(self.metrics.query_times)
            },
            "success_rates": self.metrics.success_rates,
            "error_counts": self.metrics.error_counts,
            "overall": {
                "success_rate": overall_success_rate,
                "total_operations": self.metrics.total_operations,
                "successful_operations": self.metrics.successful_operations
            }
        }
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics text"""
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus not available\n"
        
        try:
            return prom.generate_latest()
        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics: {e}")
            return "# Error generating metrics\n"
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = PerformanceMetrics()
        logger.info("Metrics reset")
    
    def export_metrics_json(self) -> str:
        """Export metrics as JSON"""
        metrics_data = self.get_current_metrics()
        metrics_data["timestamp"] = time.time()
        return json.dumps(metrics_data, indent=2)


class PerformanceTracker:
    """Performance tracking for specific components"""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.start_times = {}
        self.durations = []
        self.metrics_collector = get_metrics_collector()
    
    def start_operation(self, operation_id: str = None):
        """Start timing an operation"""
        if operation_id is None:
            operation_id = str(time.time())
        
        self.start_times[operation_id] = time.time()
        return operation_id
    
    def end_operation(self, operation_id: str, record_error: str = None):
        """End timing an operation and record metrics"""
        if operation_id not in self.start_times:
            logger.warning(f"Operation {operation_id} not found in start times")
            return None
        
        duration = time.time() - self.start_times[operation_id]
        self.durations.append(duration)
        del self.start_times[operation_id]
        
        # Record based on component type
        if self.component_name == "agent":
            self.metrics_collector.record_loop_time("unknown", duration)
        elif self.component_name == "webhook":
            self.metrics_collector.record_webhook_latency(duration)
        elif self.component_name == "pipeline":
            self.metrics_collector.record_pipeline_time(duration)
        elif self.component_name == "rag":
            self.metrics_collector.record_rag_query_time(duration)
        
        if record_error:
            self.metrics_collector.record_error(record_error, self.component_name)
        
        return duration
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.durations:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}
        
        return {
            "count": len(self.durations),
            "avg": sum(self.durations) / len(self.durations),
            "min": min(self.durations),
            "max": max(self.durations)
        }


# Global metrics collector instance
_metrics_collector: MetricsCollector = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def initialize_metrics():
    """Initialize metrics system"""
    global _metrics_collector
    _metrics_collector = MetricsCollector()
    logger.info("Metrics system initialized")


# Decorator for automatic performance tracking
def track_performance(component_name: str):
    """Decorator for automatic performance tracking"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracker = PerformanceTracker(component_name)
            operation_id = tracker.start_operation()
            
            try:
                result = func(*args, **kwargs)
                tracker.end_operation(operation_id)
                return result
            except Exception as e:
                tracker.end_operation(operation_id, str(type(e).__name__))
                raise
        
        return wrapper
    return decorator


# Context manager for performance tracking
class PerformanceContext:
    """Context manager for performance tracking"""
    
    def __init__(self, component_name: str, operation_id: str = None):
        self.component_name = component_name
        self.operation_id = operation_id
        self.tracker = PerformanceTracker(component_name)
    
    def __enter__(self):
        self.operation_id = self.tracker.start_operation(self.operation_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.tracker.end_operation(self.operation_id, str(exc_type.__name__))
        else:
            self.tracker.end_operation(self.operation_id)
    
    def get_duration(self) -> float:
        """Get current duration"""
        if self.operation_id in self.tracker.start_times:
            return time.time() - self.tracker.start_times[self.operation_id]
        return 0
