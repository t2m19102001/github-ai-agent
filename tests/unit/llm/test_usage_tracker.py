#!/usr/bin/env python3
"""
Unit tests for Usage Tracker and Cost Monitor.
"""

import pytest

from src.llm.usage_tracker import UsageTracker, CostMonitor, UsageStats
from src.llm.provider_interface import LLMResponse


class TestUsageTracker:
    """Test UsageTracker."""
    
    def test_usage_tracker_initialization(self):
        """Test usage tracker initialization."""
        tracker = UsageTracker(budget_limit=100.0)
        
        assert tracker.budget_limit == 100.0
        assert tracker._stats.total_requests == 0
    
    def test_record_usage(self):
        """Test recording usage."""
        tracker = UsageTracker()
        
        response = LLMResponse(
            content="Test",
            model="llama2-70b",
            provider="groq",
            finish_reason="stop",
            tokens_used=100,
            prompt_tokens=50,
            completion_tokens=50,
            latency_ms=500.0,
        )
        
        tracker.record_usage(response)
        
        assert tracker._stats.total_requests == 1
        assert tracker._stats.total_tokens == 100
        assert "groq" in tracker._stats.by_provider
    
    def test_cost_calculation(self):
        """Test cost calculation."""
        tracker = UsageTracker()
        
        # Groq is free
        groq_response = LLMResponse(
            content="Test",
            model="llama2-70b",
            provider="groq",
            finish_reason="stop",
            tokens_used=1000,
            prompt_tokens=500,
            completion_tokens=500,
            latency_ms=500.0,
        )
        
        cost = tracker._calculate_cost(groq_response)
        assert cost == 0.0
    
    def test_budget_check(self):
        """Test budget checking."""
        tracker = UsageTracker(budget_limit=10.0)
        
        assert tracker.check_budget() is True
    
    def test_budget_exceeded(self):
        """Test budget exceeded."""
        tracker = UsageTracker(budget_limit=1.0)
        
        # Simulate high cost (OpenAI)
        openai_response = LLMResponse(
            content="Test",
            model="gpt-4",
            provider="openai",
            finish_reason="stop",
            tokens_used=1000000,  # 1M tokens
            prompt_tokens=500000,
            completion_tokens=500000,
            latency_ms=500.0,
        )
        
        tracker.record_usage(openai_response)
        
        # Should be over budget (GPT-4 is expensive)
        assert tracker.check_budget() is False
    
    def test_get_remaining_budget(self):
        """Test getting remaining budget."""
        tracker = UsageTracker(budget_limit=100.0)
        
        remaining = tracker.get_remaining_budget()
        
        assert remaining == 100.0


class TestCostMonitor:
    """Test CostMonitor."""
    
    def test_cost_monitor_initialization(self):
        """Test cost monitor initialization."""
        tracker = UsageTracker(budget_limit=100.0)
        monitor = CostMonitor(tracker, alert_threshold=0.8)
        
        assert monitor.alert_threshold == 0.8
        assert monitor.usage_tracker == tracker
    
    def test_check_and_alert_no_alert(self):
        """Test no alert when under threshold."""
        tracker = UsageTracker(budget_limit=100.0)
        monitor = CostMonitor(tracker, alert_threshold=0.8)
        
        alert = monitor.check_and_alert()
        
        assert alert is None
    
    def test_check_and_alert_trigger(self):
        """Test alert triggered when over threshold."""
        tracker = UsageTracker(budget_limit=10.0)
        monitor = CostMonitor(tracker, alert_threshold=0.5)
        
        # Simulate 60% usage
        openai_response = LLMResponse(
            content="Test",
            model="gpt-4",
            provider="openai",
            finish_reason="stop",
            tokens_used=600000,  # 0.6M tokens
            prompt_tokens=300000,
            completion_tokens=300000,
            latency_ms=500.0,
        )
        
        tracker.record_usage(openai_response)
        
        alert = monitor.check_and_alert()
        
        # Should trigger alert (60% > 50% threshold)
        assert alert is not None
        assert alert["type"] == "budget_alert"
        assert alert["usage_ratio"] >= 0.5
    
    def test_reset_alert(self):
        """Test alert reset."""
        tracker = UsageTracker(budget_limit=10.0)
        monitor = CostMonitor(tracker, alert_threshold=0.5)
        
        # Trigger alert
        openai_response = LLMResponse(
            content="Test",
            model="gpt-4",
            provider="openai",
            finish_reason="stop",
            tokens_used=600000,
            prompt_tokens=300000,
            completion_tokens=300000,
            latency_ms=500.0,
        )
        
        tracker.record_usage(openai_response)
        monitor.check_and_alert()
        
        assert monitor._alert_triggered is True
        
        # Reset
        monitor.reset_alert()
        
        assert monitor._alert_triggered is False
