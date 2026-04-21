#!/usr/bin/env python3
"""
Token Usage Tracking and Cost Monitoring.

Production-grade implementation with:
- Token usage tracking by provider
- Cost calculation
- Budget monitoring
- Usage statistics
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .provider_interface import LLMResponse

logger = get_logger(__name__)


@dataclass
class UsageStats:
    """Usage statistics."""
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    by_provider: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class UsageTracker:
    """
    Token usage tracker.
    
    Tracks token usage and calculates costs.
    """
    
    # Pricing (per 1M tokens)
    PRICING = {
        "groq": {
            "input": 0.0,  # Groq is free
            "output": 0.0,
        },
        "openai": {
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        },
        "ollama": {
            "input": 0.0,  # Local inference is free
            "output": 0.0,
        },
    }
    
    def __init__(self, budget_limit: Optional[float] = None):
        """
        Initialize usage tracker.
        
        Args:
            budget_limit: Monthly budget limit in USD
        """
        self.budget_limit = budget_limit
        self._stats = UsageStats()
        
        logger.info(f"UsageTracker initialized (budget_limit: ${budget_limit or 'unlimited'})")
    
    def record_usage(self, response: LLMResponse):
        """
        Record token usage.
        
        Args:
            response: LLM response
        """
        self._stats.total_requests += 1
        self._stats.total_tokens += response.tokens_used
        
        # Calculate cost
        cost = self._calculate_cost(response)
        self._stats.total_cost += cost
        
        # Track by provider
        if response.provider not in self._stats.by_provider:
            self._stats.by_provider[response.provider] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0,
            }
        
        provider_stats = self._stats.by_provider[response.provider]
        provider_stats["requests"] += 1
        provider_stats["tokens"] += response.tokens_used
        provider_stats["cost"] += cost
        
        logger.debug(
            f"Recorded usage: {response.provider} "
            f"(tokens: {response.tokens_used}, cost: ${cost:.4f})"
        )
    
    def _calculate_cost(self, response: LLMResponse) -> float:
        """
        Calculate cost for response.
        
        Args:
            response: LLM response
            
        Returns:
            Cost in USD
        """
        provider_pricing = self.PRICING.get(response.provider, {})
        
        if not provider_pricing:
            # Unknown provider, assume free
            return 0.0
        
        # Get model-specific pricing
        model_pricing = provider_pricing
        if isinstance(model_pricing, dict) and response.model in model_pricing:
            model_pricing = model_pricing[response.model]
        
        # Calculate cost
        input_cost = (response.prompt_tokens / 1_000_000) * model_pricing.get("input", 0.0)
        output_cost = (response.completion_tokens / 1_000_000) * model_pricing.get("output", 0.0)
        
        return input_cost + output_cost
    
    def get_stats(self) -> UsageStats:
        """Get usage statistics."""
        return self._stats
    
    def check_budget(self) -> bool:
        """
        Check if within budget.
        
        Returns:
            True if within budget, False otherwise
        """
        if self.budget_limit is None:
            return True
        
        return self._stats.total_cost <= self.budget_limit
    
    def get_remaining_budget(self) -> Optional[float]:
        """
        Get remaining budget.
        
        Returns:
            Remaining budget in USD, or None if no limit
        """
        if self.budget_limit is None:
            return None
        
        return max(0, self.budget_limit - self._stats.total_cost)


class CostMonitor:
    """
    Cost monitor with alerting.
    
    Monitors costs and alerts when approaching budget limits.
    """
    
    def __init__(
        self,
        usage_tracker: UsageTracker,
        alert_threshold: float = 0.8,  # Alert at 80% of budget
    ):
        """
        Initialize cost monitor.
        
        Args:
            usage_tracker: Usage tracker instance
            alert_threshold: Alert threshold (0.0-1.0)
        """
        self.usage_tracker = usage_tracker
        self.alert_threshold = alert_threshold
        self._alert_triggered = False
        
        logger.info(f"CostMonitor initialized (alert_threshold: {alert_threshold})")
    
    def check_and_alert(self) -> Optional[Dict[str, Any]]:
        """
        Check budget and trigger alert if needed.
        
        Returns:
            Alert data if threshold exceeded, None otherwise
        """
        budget_limit = self.usage_tracker.budget_limit
        if budget_limit is None:
            return None
        
        current_cost = self.usage_tracker._stats.total_cost
        usage_ratio = current_cost / budget_limit
        
        if usage_ratio >= self.alert_threshold and not self._alert_triggered:
            self._alert_triggered = True
            
            alert = {
                "type": "budget_alert",
                "current_cost": current_cost,
                "budget_limit": budget_limit,
                "usage_ratio": usage_ratio,
                "remaining": budget_limit - current_cost,
                "threshold": self.alert_threshold,
            }
            
            logger.critical(
                f"Budget alert: {usage_ratio:.1%} of budget used",
                extra=alert
            )
            
            return alert
        
        return None
    
    def reset_alert(self):
        """Reset alert flag."""
        self._alert_triggered = False
        logger.info("Cost alert reset")
