#!/usr/bin/env python3
"""
Unit tests for Alerting.
"""

import pytest
from datetime import datetime

from src.observability.alerting import AlertRule, Alert, AlertManager, AlertSeverity


class TestAlertRule:
    """Test AlertRule."""
    
    def test_alert_rule_creation(self):
        """Test alert rule creation."""
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            threshold=100.0,
            comparison=">",
            severity=AlertSeverity.HIGH,
        )
        
        assert rule.name == "test_rule"
        assert rule.threshold == 100.0
        assert rule.comparison == ">"
        assert rule.severity == AlertSeverity.HIGH
    
    def test_evaluate_greater_than(self):
        """Test evaluating greater than condition."""
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            threshold=100.0,
            comparison=">",
            severity=AlertSeverity.HIGH,
        )
        
        assert rule.evaluate(150.0) is True
        assert rule.evaluate(50.0) is False
    
    def test_evaluate_less_than(self):
        """Test evaluating less than condition."""
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            threshold=100.0,
            comparison="<",
            severity=AlertSeverity.HIGH,
        )
        
        assert rule.evaluate(50.0) is True
        assert rule.evaluate(150.0) is False
    
    def test_evaluate_equal(self):
        """Test evaluating equal condition."""
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            threshold=100.0,
            comparison="=",
            severity=AlertSeverity.HIGH,
        )
        
        assert rule.evaluate(100.0) is True
        assert rule.evaluate(50.0) is False


class TestAlert:
    """Test Alert."""
    
    def test_alert_creation(self):
        """Test alert creation."""
        alert = Alert(
            rule_name="test_rule",
            severity=AlertSeverity.CRITICAL,
            message="Test alert message",
            metric_value=150.0,
            threshold=100.0,
            triggered_at=datetime.utcnow(),
        )
        
        assert alert.rule_name == "test_rule"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.metric_value == 150.0
        assert alert.threshold == 100.0
    
    def test_alert_to_dict(self):
        """Test alert serialization."""
        alert = Alert(
            rule_name="test_rule",
            severity=AlertSeverity.CRITICAL,
            message="Test alert message",
            metric_value=150.0,
            threshold=100.0,
            triggered_at=datetime.utcnow(),
        )
        
        alert_dict = alert.to_dict()
        
        assert alert_dict["rule_name"] == "test_rule"
        assert alert_dict["severity"] == "CRITICAL"
        assert alert_dict["metric_value"] == 150.0


class TestAlertManager:
    """Test AlertManager."""
    
    def test_alert_manager_initialization(self):
        """Test alert manager initialization."""
        manager = AlertManager()
        
        assert manager is not None
        assert len(manager._rules) > 0  # Should have default rules
    
    def test_register_rule(self):
        """Test registering alert rule."""
        manager = AlertManager()
        
        rule = AlertRule(
            name="custom_rule",
            description="Custom rule",
            metric_name="custom_metric",
            threshold=50.0,
            comparison=">",
            severity=AlertSeverity.MEDIUM,
        )
        
        manager.register_rule(rule)
        
        assert "custom_rule" in manager._rules
    
    def test_evaluate_metric_trigger_alert(self):
        """Test metric evaluation triggering alert."""
        manager = AlertManager()
        
        # Evaluate metric that should trigger alert
        manager.evaluate_metric("queue_depth", 1500.0)
        
        active_alerts = manager.get_active_alerts()
        
        assert len(active_alerts) > 0
    
    def test_evaluate_metric_no_alert(self):
        """Test metric evaluation not triggering alert."""
        manager = AlertManager()
        
        # Evaluate metric that should not trigger alert
        manager.evaluate_metric("queue_depth", 10.0)
        
        active_alerts = manager.get_active_alerts()
        
        # Should not have queue backlog alert
        queue_alerts = [a for a in active_alerts if a.rule_name == "queue_backlog_high"]
        assert len(queue_alerts) == 0
    
    def test_clear_alert(self):
        """Test manually clearing alert."""
        manager = AlertManager()
        
        # Trigger alert
        manager.evaluate_metric("queue_depth", 1500.0)
        
        # Clear alert
        manager.clear_alert("queue_backlog_high")
        
        active_alerts = manager.get_active_alerts()
        
        queue_alerts = [a for a in active_alerts if a.rule_name == "queue_backlog_high"]
        assert len(queue_alerts) == 0
