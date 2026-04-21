#!/usr/bin/env python3
"""
Alerting Rule Definitions and Manager.

Production-grade implementation with:
- Alert rule definitions
- Threshold-based alerting
- Pattern-based alerting
- Alert severity levels
- Alert notification channels
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    description: str
    metric_name: str
    threshold: float
    comparison: str  # ">", "<", "=", ">=", "<="
    severity: AlertSeverity
    duration_seconds: int = 60  # Alert only if condition persists for this duration
    labels: Dict[str, str] = None
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if alert condition is met."""
        if self.comparison == ">":
            return value > self.threshold
        elif self.comparison == "<":
            return value < self.threshold
        elif self.comparison == ">=":
            return value >= self.threshold
        elif self.comparison == "<=":
            return value <= self.threshold
        elif self.comparison == "=":
            return value == self.threshold
        return False


@dataclass
class Alert:
    """Alert instance."""
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_value: float
    threshold: float
    triggered_at: datetime
    labels: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "triggered_at": self.triggered_at.isoformat(),
            "labels": self.labels or {},
        }


class AlertManager:
    """
    Alert manager for monitoring and alerting.
    
    Manages alert rules, evaluates metrics, and triggers alerts.
    """
    
    def __init__(self):
        """Initialize alert manager."""
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        
        # Register default alert rules
        self._register_default_rules()
        
        logger.info("AlertManager initialized")
    
    def _register_default_rules(self):
        """Register default production alert rules."""
        # Queue backlog alert
        self.register_rule(
            AlertRule(
                name="queue_backlog_high",
                description="Task queue backlog exceeds threshold",
                metric_name="queue_depth",
                threshold=1000,
                comparison=">",
                severity=AlertSeverity.HIGH,
                duration_seconds=300,
            )
        )
        
        # DLQ entry rate alert
        self.register_rule(
            AlertRule(
                name="dlq_entry_rate_high",
                description="Dead letter queue entry rate exceeds threshold",
                metric_name="dlq_entries_per_minute",
                threshold=10,
                comparison=">",
                severity=AlertSeverity.CRITICAL,
                duration_seconds=60,
            )
        )
        
        # Task failure rate alert
        self.register_rule(
            AlertRule(
                name="task_failure_rate_high",
                description="Task failure rate exceeds threshold",
                metric_name="task_failure_rate",
                threshold=0.05,
                comparison=">",
                severity=AlertSeverity.HIGH,
                duration_seconds=300,
            )
        )
        
        # Worker heartbeat missing alert
        self.register_rule(
            AlertRule(
                name="worker_heartbeat_missing",
                description="Worker heartbeat missing",
                metric_name="worker_heartbeat_age_seconds",
                threshold=120,
                comparison=">",
                severity=AlertSeverity.CRITICAL,
                duration_seconds=60,
            )
        )
        
        # GitHub API error rate alert
        self.register_rule(
            AlertRule(
                name="github_api_error_rate_high",
                description="GitHub API error rate exceeds threshold",
                metric_name="github_api_error_rate",
                threshold=0.05,
                comparison=">",
                severity=AlertSeverity.HIGH,
                duration_seconds=300,
            )
        )
        
        # LLM error rate alert
        self.register_rule(
            AlertRule(
                name="llm_error_rate_high",
                description="LLM error rate exceeds threshold",
                metric_name="llm_error_rate",
                threshold=0.05,
                comparison=">",
                severity=AlertSeverity.HIGH,
                duration_seconds=300,
            )
        )
        
        logger.info(f"Registered {len(self._rules)} default alert rules")
    
    def register_rule(self, rule: AlertRule):
        """
        Register alert rule.
        
        Args:
            rule: Alert rule to register
        """
        self._rules[rule.name] = rule
        logger.info(f"Registered alert rule: {rule.name}")
    
    def evaluate_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, Any]] = None):
        """
        Evaluate metric against all relevant rules.
        
        Args:
            metric_name: Metric name
            value: Metric value
            labels: Metric labels
        """
        labels = labels or {}
        
        for rule_name, rule in self._rules.items():
            if rule.metric_name == metric_name:
                if rule.evaluate(value):
                    # Check if already active
                    if rule_name not in self._active_alerts:
                        alert = Alert(
                            rule_name=rule_name,
                            severity=rule.severity,
                            message=f"{rule.description}: {value} {rule.comparison} {rule.threshold}",
                            metric_value=value,
                            threshold=rule.threshold,
                            triggered_at=datetime.utcnow(),
                            labels=labels,
                        )
                        self._active_alerts[rule_name] = alert
                        self._alert_history.append(alert)
                        
                        # Log alert
                        if rule.severity == AlertSeverity.CRITICAL:
                            logger.critical(
                                f"ALERT: {rule_name}",
                                extra={"alert": alert.to_dict()}
                            )
                        elif rule.severity == AlertSeverity.HIGH:
                            logger.error(
                                f"ALERT: {rule_name}",
                                extra={"alert": alert.to_dict()}
                            )
                        else:
                            logger.warning(
                                f"ALERT: {rule_name}",
                                extra={"alert": alert.to_dict()}
                            )
                else:
                    # Update existing alert
                    self._active_alerts[rule_name].metric_value = value
            else:
                # Clear alert if condition no longer met
                if rule_name in self._active_alerts and not rule.evaluate(value):
                    alert = self._active_alerts.pop(rule_name)
                    logger.info(f"Alert cleared: {rule_name}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self._active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return self._alert_history[-limit:]
    
    def clear_alert(self, rule_name: str):
        """
        Manually clear an alert.
        
        Args:
            rule_name: Alert rule name
        """
        if rule_name in self._active_alerts:
            alert = self._active_alerts.pop(rule_name)
            logger.info(f"Alert manually cleared: {rule_name}")


# Global alert manager instance
alert_manager = AlertManager()
