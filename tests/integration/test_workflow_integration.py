#!/usr/bin/env python3
"""
Integration tests for full workflow.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.workflow.orchestrator import WorkflowOrchestrator, WorkflowStatus
from src.workflow.workflow_context import WorkflowContext


@pytest.mark.integration
class TestWorkflowIntegration:
    """Test full workflow integration."""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create workflow orchestrator for testing."""
        # Mock dependencies
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
    async def test_full_workflow_for_issue_event(self, orchestrator):
        """Test full workflow for GitHub issue event."""
        # Prepare webhook payload
        payload = '{"action": "opened", "issue": {"number": 123, "title": "Test issue"}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        # Mock signature verification
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        
        # Mock idempotency
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        
        # Mock task queue
        orchestrator.task_queue.enqueue = AsyncMock()
        
        # Mock audit store
        orchestrator.audit_store.append = AsyncMock()
        
        # Process webhook
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        # Verify workflow completed
        assert result.status == WorkflowStatus.COMPLETED
        assert result.context.github_event_type == "issues"
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_full_workflow_for_pr_event(self, orchestrator):
        """Test full workflow for GitHub pull request event."""
        # Prepare webhook payload
        payload = '{"action": "opened", "pull_request": {"number": 456, "title": "Test PR"}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "pull_request",
        }
        
        # Mock signature verification
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        
        # Mock idempotency
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        
        # Mock task queue
        orchestrator.task_queue.enqueue = AsyncMock()
        
        # Mock audit store
        orchestrator.audit_store.append = AsyncMock()
        
        # Process webhook
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        # Verify workflow completed
        assert result.status == WorkflowStatus.COMPLETED
        assert result.context.github_event_type == "pull_request"
    
    @pytest.mark.asyncio
    async def test_idempotency_handling(self, orchestrator):
        """Test idempotency handling for duplicate webhooks."""
        # Prepare webhook payload
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        # Mock signature verification
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        
        # Mock idempotency as duplicate
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=True)
        
        # Process webhook
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        # Verify workflow completed early due to duplicate
        assert result.status == WorkflowStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_signature_validation_failure(self, orchestrator):
        """Test signature validation failure."""
        # Prepare webhook payload
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "invalid_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        # Mock signature verification as failed
        orchestrator.signature_verifier.verify = MagicMock(return_value=False)
        
        # Process webhook
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        # Verify workflow failed
        assert result.status == WorkflowStatus.FAILED
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_distributed_tracing_preserved(self, orchestrator):
        """Test distributed tracing is preserved across workflow."""
        # Prepare webhook payload
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        # Mock dependencies
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock()
        orchestrator.audit_store.append = AsyncMock()
        
        # Process webhook
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        # Verify trace context is set
        assert result.context.trace_context is not None
        assert result.context.request_id is not None
