#!/usr/bin/env python3
"""
Unit tests for Retry Policy Engine.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta

from src.infrastructure.retry.retry_policy import (
    RetryPolicy,
    ExponentialBackoff,
    RetryDecision,
    MaxRetriesExceededError,
    ValidationError,
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
    SecurityError,
    RateLimitError,
    LLMProviderError,
    GitHubAPIError,
    DatabaseError,
)


class TestExponentialBackoff:
    """Test exponential backoff with jitter."""
    
    def test_exponential_backoff_initialization(self):
        """Test backoff initialization."""
        backoff = ExponentialBackoff(
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
        )
        
        assert backoff.base_delay == 1.0
        assert backoff.max_delay == 60.0
        assert backoff.exponential_base == 2.0
        assert backoff.jitter is True
    
    def test_exponential_backoff_calculation(self):
        """Test backoff calculation without jitter."""
        backoff = ExponentialBackoff(
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=False,
        )
        
        # Test exponential progression
        assert backoff.calculate(0) == 1.0
        assert backoff.calculate(1) == 2.0
        assert backoff.calculate(2) == 4.0
        assert backoff.calculate(3) == 8.0
    
    def test_exponential_backoff_max_delay(self):
        """Test backoff respects max delay."""
        backoff = ExponentialBackoff(
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=False,
        )
        
        # Should cap at max_delay
        assert backoff.calculate(0) == 1.0
        assert backoff.calculate(1) == 2.0
        assert backoff.calculate(2) == 4.0
        assert backoff.calculate(3) == 8.0
        assert backoff.calculate(4) == 10.0  # Capped
        assert backoff.calculate(5) == 10.0  # Capped
    
    def test_exponential_backoff_with_jitter(self):
        """Test jitter adds randomness."""
        backoff = ExponentialBackoff(
            base_delay=10.0,
            max_delay=60.0,
            jitter=True,
        )
        
        delays = [backoff.calculate(0) for _ in range(10)]
        
        # With jitter, delays should vary
        # Base delay is 10, so jitter should produce values between 0 and 10
        assert all(0 <= d <= 10 for d in delays)
    
    def test_exponential_backoff_no_jitter(self):
        """Test no jitter produces deterministic values."""
        backoff = ExponentialBackoff(
            base_delay=1.0,
            max_delay=60.0,
            jitter=False,
        )
        
        delay1 = backoff.calculate(2)
        delay2 = backoff.calculate(2)
        
        # Without jitter, should be deterministic
        assert delay1 == delay2


class TestRetryPolicy:
    """Test retry policy logic."""
    
    @pytest.fixture
    def retry_policy(self):
        """Create retry policy instance."""
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=60.0)
        return RetryPolicy(max_attempts=3, backoff=backoff)
    
    def test_retry_policy_initialization(self):
        """Test retry policy initialization."""
        backoff = ExponentialBackoff()
        policy = RetryPolicy(max_attempts=3, backoff=backoff)
        
        assert policy.max_attempts == 3
        assert policy.backoff == backoff
    
    def test_should_retry_fatal_exception(self, retry_policy):
        """Test fatal exceptions are not retried."""
        exc = ValidationError("Validation failed")
        
        result = retry_policy.should_retry(exc, attempt=0)
        
        assert result.should_retry is False
        assert "not retryable" in result.reason
    
    def test_should_retry_connection_error(self, retry_policy):
        """Test connection errors are retried."""
        exc = ConnectionError("Connection failed")
        
        result = retry_policy.should_retry(exc, attempt=0)
        
        assert result.should_retry is True
        assert result.attempt == 0
    
    def test_should_retry_max_attempts_exceeded(self, retry_policy):
        """Test max attempts enforcement."""
        exc = ConnectionError("Connection failed")
        
        result = retry_policy.should_retry(exc, attempt=3)
        
        assert result.should_retry is False
        assert "Max attempts" in result.reason
    
    def test_should_retry_timeout_error(self, retry_policy):
        """Test timeout errors are retried."""
        exc = TimeoutError("Request timeout")
        
        result = retry_policy.should_retry(exc, attempt=0)
        
        assert result.should_retry is True
        assert result.delay_seconds > 0
    
    def test_execute_with_retry_success(self, retry_policy):
        """Test successful execution without retry."""
        async def success_operation():
            return "success"
        
        result = asyncio.run(retry_policy.execute_with_retry(success_operation))
        
        assert result == "success"
    
    def test_execute_with_retry_failure(self, retry_policy):
        """Test failed execution with retry."""
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Failed")
            return "success"
        
        result = asyncio.run(retry_policy.execute_with_retry(failing_operation))
        
        assert result == "success"
        assert call_count == 2
    
    def test_execute_with_retry_max_retries(self, retry_policy):
        """Test max retries exceeded."""
        async def always_failing():
            raise ConnectionError("Always fails")
        
        with pytest.raises(MaxRetriesExceededError):
            asyncio.run(retry_policy.execute_with_retry(always_failing))


class TestRetryClassifier:
    """Test retry classifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return RetryClassifier()
    
    def test_classify_fatal_exception(self, classifier):
        """Test fatal exception classification."""
        exc = ValidationError("Validation failed")
        
        decision = classifier.classify(exc)
        
        assert decision == RetryDecision.DO_NOT_RETRY
    
    def test_classify_retryable_exception(self, classifier):
        """Test retryable exception classification."""
        exc = ConnectionError("Connection failed")
        
        decision = classifier.classify(exc)
        
        assert decision == RetryDecision.RETRY
    
    def test_custom_classifier_registration(self, classifier):
        """Test custom classifier registration."""
        def custom_classifier(exc, context):
            return RetryDecision.IMMEDIATE_RETRY
        
        classifier.register_classifier(ValueError, custom_classifier)
        
        exc = ValueError("Test error")
        decision = classifier.classify(exc)
        
        assert decision == RetryDecision.IMMEDIATE_RETRY
