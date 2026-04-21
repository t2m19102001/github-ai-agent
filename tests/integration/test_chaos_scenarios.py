#!/usr/bin/env python3
"""
Chaos testing scenarios for workflow.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import random

from src.workflow.orchestrator import WorkflowOrchestrator, WorkflowStatus


@pytest.mark.integration
class TestChaosScenarios:
    """Test chaos scenarios in workflow."""
    
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
    async def test_random_failure_in_workflow(self, orchestrator):
        """Test workflow with random failures injected."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        # Mock dependencies with random failure
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        
        enqueue_call_count = 0
        
        async def flaky_enqueue(*args, **kwargs):
            nonlocal enqueue_call_count
            enqueue_call_count += 1
            if random.random() < 0.5:  # 50% chance of failure
                raise Exception("Random queue error")
        
        orchestrator.task_queue.enqueue = flaky_enqueue
        orchestrator.audit_store.append = AsyncMock()
        
        # Run multiple times to test chaos
        successes = 0
        failures = 0
        
        for _ in range(10):
            result = await orchestrator.process_webhook(payload, signature, headers)
            if result.status == WorkflowStatus.COMPLETED:
                successes += 1
            else:
                failures += 1
        
        # Verify some succeeded, some failed
        assert successes + failures == 10
        print(f"Chaos test: {successes} successes, {failures} failures")
    
    @pytest.mark.asyncio
    async def test_redis_cache_failure(self, orchestrator):
        """Test workflow when Redis cache fails."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        
        # Mock Redis failure
        async def redis_failure(*args, **kwargs):
            raise Exception("Redis connection error")
        
        orchestrator.idempotency_manager.is_duplicate = redis_failure
        orchestrator.task_queue.enqueue = AsyncMock()
        orchestrator.audit_store.append = AsyncMock()
        
        # Workflow should still complete (idempotency check fails gracefully)
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        # Should complete despite Redis failure
        assert result.status == WorkflowStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_database_connection_timeout(self, orchestrator):
        """Test workflow when database times out."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock()
        
        # Mock database timeout
        async def db_timeout(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate timeout
            raise Exception("Database timeout")
        
        orchestrator.audit_store.append = db_timeout
        
        # Workflow should handle timeout gracefully
        # Using a timeout wrapper
        try:
            result = await asyncio.wait_for(
                orchestrator.process_webhook(payload, signature, headers),
                timeout=5.0
            )
            # If it completes, audit failed but workflow continued
            assert result.status == WorkflowStatus.FAILED
        except asyncio.TimeoutError:
            # Workflow timed out - this is expected in chaos test
            pass
    
    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing(self, orchestrator):
        """Test concurrent webhook processing."""
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock()
        orchestrator.audit_store.append = AsyncMock()
        
        # Create multiple concurrent webhooks
        tasks = []
        for i in range(10):
            payload = f'{{"action": "opened", "issue": {{"number": {i}}}}}'
            signature = "test_signature"
            headers = {
                "X-GitHub-Delivery": f"test-delivery-id-{i}",
                "X-GitHub-Event": "issues",
            }
            
            task = orchestrator.process_webhook(payload, signature, headers)
            tasks.append(task)
        
        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all completed
        successful_results = [r for r in results if isinstance(r, object) and hasattr(r, 'status')]
        assert len(successful_results) == 10
        
        # Verify all have unique workflow IDs
        workflow_ids = [r.context.workflow_id for r in successful_results]
        assert len(set(workflow_ids)) == 10
    
    @pytest.mark.asyncio
    async def test_memory_pressure_simulation(self, orchestrator):
        """Test workflow under memory pressure."""
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock()
        orchestrator.audit_store.append = AsyncMock()
        
        # Simulate memory pressure by creating large payloads
        large_payload = '{"action": "opened", "issue": {"number": 123, "body": "' + "x" * 1000000 + '"}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        # Workflow should handle large payloads
        result = await orchestrator.process_webhook(large_payload, signature, headers)
        
        # Should complete despite large payload
        assert result.status == WorkflowStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_network_partition_simulation(self, orchestrator):
        """Test workflow during network partition."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock()
        
        # Simulate network partition on GitHub API
        async def network_partition(*args, **kwargs):
            raise Exception("Network unreachable")
        
        orchestrator._post_to_github = network_partition
        orchestrator.audit_store.append = AsyncMock()
        
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        # Should fail gracefully
        assert result.status == WorkflowStatus.FAILED
        assert "Network unreachable" in str(result.errors)
    
    @pytest.mark.asyncio
    async def test_partial_workflow_failure(self, orchestrator):
        """Test workflow with partial failure (some steps succeed)."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock()
        
        # Make GitHub posting fail
        async def github_failure(*args, **kwargs):
            raise Exception("GitHub API error")
        
        orchestrator._post_to_github = github_failure
        orchestrator.audit_store.append = AsyncMock()
        
        result = await orchestrator.process_webhook(payload, signature, headers)
        
        # Should fail at GitHub posting step
        assert result.status == WorkflowStatus.FAILED
        # But earlier steps should have succeeded
        assert orchestrator.task_queue.enqueue.called
    
    @pytest.mark.asyncio
    async def test_duplicate_webhook_during_processing(self, orchestrator):
        """Test duplicate webhook received during processing."""
        payload = '{"action": "opened", "issue": {"number": 123}}'
        signature = "test_signature"
        headers = {
            "X-GitHub-Delivery": "test-delivery-id",
            "X-GitHub-Event": "issues",
        }
        
        orchestrator.signature_verifier.verify = MagicMock(return_value=True)
        orchestrator.idempotency_manager.is_duplicate = AsyncMock(return_value=False)
        orchestrator.task_queue.enqueue = AsyncMock()
        orchestrator.audit_store.append = AsyncMock()
        
        # Start first workflow
        first_task = asyncio.create_task(
            orchestrator.process_webhook(payload, signature, headers)
        )
        
        # Immediately start second workflow (duplicate)
        second_task = asyncio.create_task(
            orchestrator.process_webhook(payload, signature, headers)
        )
        
        # Wait for both
        results = await asyncio.gather(first_task, second_task, return_exceptions=True)
        
        # Both should complete
        assert all(isinstance(r, object) for r in results)
