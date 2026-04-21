#!/usr/bin/env python3
"""
Failure simulation tests for workflow.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.workflow.orchestrator import WorkflowOrchestrator, WorkflowStatus
from src.workflow.retry_handler import WorkflowRetryHandler, RetryConfig


@pytest.mark.integration
class TestFailureSimulation:
    """Test failure scenarios in workflow."""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create workflow orchestrator for testing."""
        db_session_factory = AsyncMock()
        redis_client = AsyncMock()
        github_client = AsyncMock()
        
        orchestrator = WorkflowOrchestrator(
            webhook_secret="test_secret",
            db_session_factory=db_session_factory,
            redis_client=redis_client,
            github_client=github_client,
        )
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_webhook_signature_failure(self, orchestrator):
        """Test webhook signature validation failure."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "invalid_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        orchestrator.signature_verifier.verify = MagicMock(return_value=False)
        
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        assert result.status == WorkflowStatus.FAILED
        assert "Invalid webhook signature" in str(result.errors)
    
    @pytest.mark.asyncio
    async def test_queue_failure(self, orchestrator):
        """Test queue enqueue failure."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock(side_effect=Exception("Queue error"))
        
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        assert result.status == WorkflowStatus.FAILED
        assert "Queue error" in str(result.errors)
    
    @pytest.mark.asyncio
    async def test_database_failure(self, orchestrator):
        """Test database operation failure."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock()
        orchestrator.audit_store.append = AsyncMock(side_effect=Exception("DB error"))
        
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        assert result.status == WorkflowStatus.FAILED
        # Audit failure shouldn't stop the workflow, but it should be logged
    
    @pytest.mark.asyncio
    async def test_github_api_failure(self, orchestrator):
        """Test GitHub API failure during posting."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock()
        
        # Mock GitHub client failure
        async def mock_post_to_github(*args, **kwargs):
            raise Exception("GitHub API error")
        
        orchestrator._post_to_github = mock_post_to_github
        orchestrator.audit_store.append = AsyncMock()
        
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        assert result.status == WorkflowStatus.FAILED
        assert "GitHub API error" in str(result.errors)


@pytest.mark.integration
class TestRetryHandler:
    """Test retry handler with failures."""
    
    @pytest.mark.asyncio
    async def test_successful_operation_no_retry(self):
        """Test successful operation doesn't retry."""
        handler = WorkflowRetryHandler()
        
        async def successful_operation():
            return "success"
        
        result = await handler.execute_with_retry(
            successful_operation,
            "test_operation"
        )
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test retry on transient failure."""
        handler = WorkflowRetryHandler(RetryConfig(max_retries=3, base_delay=0.1))
        
        attempt_count = 0
        
        async def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Transient error")
            return "success"
        
        result = await handler.execute_with_retry(
            flaky_operation,
            "test_operation"
        )
        
        assert result == "success"
        assert attempt_count == 3
    
    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test exhausted retries raises exception."""
        handler = WorkflowRetryHandler(RetryConfig(max_retries=2, base_delay=0.1))
        
        async def always_failing_operation():
            raise Exception("Permanent error")
        
        with pytest.raises(Exception, match="Permanent error"):
            await handler.execute_with_retry(
                always_failing_operation,
                "test_operation"
            )
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test non-retryable exceptions are not retried."""
        handler = WorkflowRetryHandler(RetryConfig(max_retries=3, base_delay=0.1))
        
        attempt_count = 0
        
        async def value_error_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError):
            await handler.execute_with_retry(
                value_error_operation,
                "test_operation"
            )
        
        # Should only attempt once
        assert attempt_count == 1
