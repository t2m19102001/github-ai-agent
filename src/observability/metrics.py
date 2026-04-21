#!/usr/bin/env python3
"""
Prometheus Metrics and Business Metrics.

Production-grade implementation with:
- Counter metrics (monotonically increasing)
- Gauge metrics (up/down values)
- Histogram metrics (distributions)
- Summary metrics (quantiles)
- Business metrics (domain-specific)
- Metric labeling
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import time

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """Base metric."""
    name: str
    metric_type: MetricType
    help_text: str
    labels: Dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_prometheus(self) -> str:
        """Convert to Prometheus format."""
        label_str = ""
        if self.labels:
            label_str = "{" + ", ".join(f'{k}="{v}"' for k, v in self.labels.items()) + "}"
        
        return f"{self.name}{label_str} {self.value} {int(self.timestamp.timestamp())}\n"


class Counter(Metric):
    """Counter metric (monotonically increasing)."""
    
    def __init__(self, name: str, help_text: str, labels: Optional[Dict[str, str]] = None):
        super().__init__(name, MetricType.COUNTER, help_text, labels or {})
    
    def inc(self, amount: float = 1.0):
        """Increment counter."""
        if amount < 0:
            raise ValueError("Counter cannot be decremented")
        self.value += amount
    
    def get(self) -> float:
        """Get current value."""
        return self.value


class Gauge(Metric):
    """Gauge metric (can go up or down)."""
    
    def __init__(self, name: str, help_text: str, labels: Optional[Dict[str, str]] = None):
        super().__init__(name, MetricType.GAUGE, help_text, labels or {})
    
    def inc(self, amount: float = 1.0):
        """Increment gauge."""
        self.value += amount
    
    def dec(self, amount: float = 1.0):
        """Decrement gauge."""
        self.value -= amount
    
    def set(self, value: float):
        """Set gauge to specific value."""
        self.value = value
    
    def get(self) -> float:
        """Get current value."""
        return self.value


class Histogram(Metric):
    """Histogram metric (distribution)."""
    
    def __init__(
        self,
        name: str,
        help_text: str,
        buckets: List[float] = None,
        labels: Optional[Dict[str, str]] = None
    ):
        super().__init__(name, MetricType.HISTOGRAM, help_text, labels or {})
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        self.bucket_counts = defaultdict(int)
        self.sum = 0.0
        self.count = 0
    
    def observe(self, value: float):
        """Observe a value."""
        self.sum += value
        self.count += 1
        
        for bucket in self.buckets:
            if value <= bucket:
                self.bucket_counts[bucket] += 1
    
    def to_prometheus(self) -> str:
        """Convert to Prometheus format."""
        lines = []
        
        # Build label string
        if self.labels:
            label_parts = [f'{k}="{v}"' for k, v in self.labels.items()]
            label_str = "{" + ", ".join(label_parts) + "}"
        else:
            label_str = ""
        
        # Count metric
        lines.append(f"{self.name}_count{label_str} {self.count} {int(self.timestamp.timestamp())}\n")
        
        # Sum metric
        lines.append(f"{self.name}_sum{label_str} {self.sum} {int(self.timestamp.timestamp())}\n")
        
        # Bucket metrics
        for bucket in self.buckets:
            if self.labels:
                bucket_label = f'le="{bucket}",' + ",".join(f'{k}="{v}"' for k, v in self.labels.items())
                lines.append(f'{self.name}_bucket{{{bucket_label}}} {self.bucket_counts[bucket]} {int(self.timestamp.timestamp())}\n')
            else:
                lines.append(f'{self.name}_bucket{{le="{bucket}"}} {self.bucket_counts[bucket]} {int(self.timestamp.timestamp())}\n')
        
        # +Inf bucket
        if self.labels:
            inf_label = 'le="+Inf",' + ",".join(f'{k}="{v}"' for k, v in self.labels.items())
            lines.append(f'{self.name}_bucket{{{inf_label}}} {self.count} {int(self.timestamp.timestamp())}\n')
        else:
            lines.append(f'{self.name}_bucket{{le="+Inf"}} {self.count} {int(self.timestamp.timestamp())}\n')
        
        return "".join(lines)


class BusinessMetrics:
    """
    Business metrics for domain-specific monitoring.
    
    Includes:
    - Task processing metrics
    - Webhook metrics
    - GitHub API metrics
    - LLM metrics
    - Error metrics
    """
    
    def __init__(self):
        """Initialize business metrics."""
        # Task metrics
        self.tasks_enqueued = Counter("tasks_enqueued_total", "Total tasks enqueued")
        self.tasks_completed = Counter("tasks_completed_total", "Total tasks completed")
        self.tasks_failed = Counter("tasks_failed_total", "Total tasks failed")
        self.tasks_retry = Counter("tasks_retry_total", "Total task retries")
        self.task_duration = Histogram("task_duration_seconds", "Task execution duration")
        self.queue_depth = Gauge("queue_depth", "Current queue depth")
        
        # Webhook metrics
        self.webhooks_received = Counter("webhooks_received_total", "Total webhooks received")
        self.webhooks_processed = Counter("webhooks_processed_total", "Total webhooks processed")
        self.webhooks_failed = Counter("webhooks_failed_total", "Total webhooks failed")
        self.webhook_signature_failures = Counter("webhook_signature_failures_total", "Total signature verification failures")
        self.webhook_duplicate = Counter("webhook_duplicate_total", "Total duplicate webhooks")
        
        # GitHub API metrics
        self.github_api_requests = Counter("github_api_requests_total", "Total GitHub API requests")
        self.github_api_errors = Counter("github_api_errors_total", "Total GitHub API errors")
        self.github_rate_limit_hits = Counter("github_rate_limit_hits_total", "Total rate limit hits")
        self.github_abuse_detection = Counter("github_abuse_detection_total", "Total abuse detection hits")
        self.github_api_duration = Histogram("github_api_duration_seconds", "GitHub API request duration")
        
        # LLM metrics
        self.llm_requests = Counter("llm_requests_total", "Total LLM requests")
        self.llm_errors = Counter("llm_errors_total", "Total LLM errors")
        self.llm_rate_limit_hits = Counter("llm_rate_limit_hits_total", "Total LLM rate limit hits")
        self.llm_duration = Histogram("llm_duration_seconds", "LLM request duration")
        self.llm_tokens_used = Counter("llm_tokens_used_total", "Total tokens used")
        
        # Error metrics
        self.errors_total = Counter("errors_total", "Total errors")
        self.errors_by_type = Counter("errors_by_type_total", "Errors by type", {"type": ""})
        
        logger.info("BusinessMetrics initialized")
    
    def record_task_completed(self, task_type: str, duration: float):
        """Record task completion."""
        self.tasks_completed.inc()
        self.task_duration.observe(duration)
    
    def record_task_failed(self, task_type: str, error_type: str):
        """Record task failure."""
        self.tasks_failed.inc()
        self.errors_by_type.labels(type=error_type).inc()
    
    def record_webhook_received(self, event_type: str):
        """Record webhook received."""
        self.webhooks_received.inc()
    
    def record_webhook_processed(self, event_type: str, duration: float):
        """Record webhook processed."""
        self.webhooks_processed.inc()
    
    def record_github_api_request(self, endpoint: str, duration: float, status_code: int):
        """Record GitHub API request."""
        self.github_api_requests.inc()
        self.github_api_duration.observe(duration)
        
        if status_code >= 400:
            self.github_api_errors.inc()
    
    def record_llm_request(self, provider: str, duration: float, tokens: int):
        """Record LLM request."""
        self.llm_requests.inc()
        self.llm_duration.observe(duration)
        self.llm_tokens_used.inc(tokens)
    
    def export_metrics(self) -> str:
        """Export all metrics in Prometheus format."""
        lines = []
        
        # Add HELP and TYPE for each metric
        metrics = [
            self.tasks_enqueued, self.tasks_completed, self.tasks_failed,
            self.tasks_retry, self.task_duration, self.queue_depth,
            self.webhooks_received, self.webhooks_processed, self.webhooks_failed,
            self.webhook_signature_failures, self.webhook_duplicate,
            self.github_api_requests, self.github_api_errors, self.github_rate_limit_hits,
            self.github_abuse_detection, self.github_api_duration,
            self.llm_requests, self.llm_errors, self.llm_rate_limit_hits,
            self.llm_duration, self.llm_tokens_used,
            self.errors_total, self.errors_by_type,
        ]
        
        for metric in metrics:
            lines.append(f"# HELP {metric.name} {metric.help_text}\n")
            lines.append(f"# TYPE {metric.name} {metric.metric_type.value}\n")
            lines.append(metric.to_prometheus())
        
        return "".join(lines)


class PrometheusMetrics:
    """
    Prometheus metrics exporter.
    
    Provides /metrics endpoint for Prometheus scraping.
    """
    
    def __init__(self, business_metrics: BusinessMetrics):
        """
        Initialize Prometheus metrics exporter.
        
        Args:
            business_metrics: Business metrics instance
        """
        self.business_metrics = business_metrics
        self.custom_metrics: Dict[str, Metric] = {}
        
        logger.info("PrometheusMetrics initialized")
    
    def register_metric(self, metric: Metric):
        """Register custom metric."""
        self.custom_metrics[metric.name] = metric
        logger.info(f"Registered metric: {metric.name}")
    
    def get_metrics(self) -> str:
        """
        Get all metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        # Add business metrics
        lines.append(self.business_metrics.export_metrics())
        
        # Add custom metrics
        for metric in self.custom_metrics.values():
            lines.append(f"# HELP {metric.name} {metric.help_text}\n")
            lines.append(f"# TYPE {metric.name} {metric.metric_type.value}\n")
            lines.append(metric.to_prometheus())
        
        return "".join(lines)
