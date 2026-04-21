#!/usr/bin/env python3
"""
Unit tests for Metrics.
"""

import pytest

from src.observability.metrics import Counter, Gauge, Histogram, BusinessMetrics


class TestCounter:
    """Test Counter metric."""
    
    def test_counter_creation(self):
        """Test counter creation."""
        counter = Counter("test_counter", "Test counter")
        
        assert counter.name == "test_counter"
        assert counter.metric_type.value == "counter"
        assert counter.value == 0.0
    
    def test_counter_increment(self):
        """Test counter increment."""
        counter = Counter("test_counter", "Test counter")
        
        counter.inc()
        assert counter.value == 1.0
        
        counter.inc(5.0)
        assert counter.value == 6.0
    
    def test_counter_cannot_decrement(self):
        """Test counter cannot be decremented."""
        counter = Counter("test_counter", "Test counter")
        
        with pytest.raises(ValueError):
            counter.dec()
    
    def test_counter_to_prometheus(self):
        """Test counter Prometheus format."""
        counter = Counter("test_counter", "Test counter")
        counter.inc()
        
        prometheus = counter.to_prometheus()
        
        assert "test_counter" in prometheus
        assert "1.0" in prometheus


class TestGauge:
    """Test Gauge metric."""
    
    def test_gauge_creation(self):
        """Test gauge creation."""
        gauge = Gauge("test_gauge", "Test gauge")
        
        assert gauge.name == "test_gauge"
        assert gauge.metric_type.value == "gauge"
        assert gauge.value == 0.0
    
    def test_gauge_increment(self):
        """Test gauge increment."""
        gauge = Gauge("test_gauge", "Test gauge")
        
        gauge.inc()
        assert gauge.value == 1.0
    
    def test_gauge_decrement(self):
        """Test gauge decrement."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(10.0)
        
        gauge.dec()
        assert gauge.value == 9.0
    
    def test_gauge_set(self):
        """Test gauge set."""
        gauge = Gauge("test_gauge", "Test gauge")
        
        gauge.set(42.0)
        assert gauge.value == 42.0


class TestHistogram:
    """Test Histogram metric."""
    
    def test_histogram_creation(self):
        """Test histogram creation."""
        histogram = Histogram("test_histogram", "Test histogram")
        
        assert histogram.name == "test_histogram"
        assert histogram.metric_type.value == "histogram"
        assert histogram.count == 0
        assert histogram.sum == 0.0
    
    def test_histogram_observe(self):
        """Test histogram observe."""
        histogram = Histogram("test_histogram", "Test histogram")
        
        histogram.observe(0.1)
        histogram.observe(0.5)
        histogram.observe(1.0)
        
        assert histogram.count == 3
        assert histogram.sum == 1.6
    
    def test_histogram_buckets(self):
        """Test histogram bucket counting."""
        histogram = Histogram("test_histogram", "Test histogram")
        
        histogram.observe(0.01)
        histogram.observe(0.05)
        histogram.observe(0.1)
        
        assert histogram.bucket_counts[0.01] == 1
        assert histogram.bucket_counts[0.05] == 2
        assert histogram.bucket_counts[0.1] == 3


class TestBusinessMetrics:
    """Test BusinessMetrics."""
    
    def test_business_metrics_initialization(self):
        """Test business metrics initialization."""
        metrics = BusinessMetrics()
        
        assert metrics.tasks_enqueued is not None
        assert metrics.tasks_completed is not None
        assert metrics.webhooks_received is not None
        assert metrics.github_api_requests is not None
        assert metrics.llm_requests is not None
    
    def test_record_task_completed(self):
        """Test recording task completion."""
        metrics = BusinessMetrics()
        
        metrics.record_task_completed("test_task", 5.0)
        
        assert metrics.tasks_completed.get() == 1
    
    def test_record_task_failed(self):
        """Test recording task failure."""
        metrics = BusinessMetrics()
        
        metrics.record_task_failed("test_task", "timeout")
        
        assert metrics.tasks_failed.get() == 1
    
    def test_record_webhook_received(self):
        """Test recording webhook received."""
        metrics = BusinessMetrics()
        
        metrics.record_webhook_received("issues")
        
        assert metrics.webhooks_received.get() == 1
    
    def test_export_metrics(self):
        """Test exporting metrics."""
        metrics = BusinessMetrics()
        
        metrics.tasks_enqueued.inc()
        metrics.tasks_completed.inc()
        
        exported = metrics.export_metrics()
        
        assert "tasks_enqueued_total" in exported
        assert "tasks_completed_total" in exported
