#!/usr/bin/env python3
"""
Integration tests for webhook security and guardrails
"""

import pytest
import json
import hmac
import hashlib
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import Request

from src.web.webhooks import (
    WebhookSecurity, 
    WebhookProcessor,
    github_webhook_handler,
    webhook_health_check,
    webhook_metrics
)
from src.security.guardrails import SecurityError, security_guardrails


class TestWebhookSecurity:
    """Test webhook security verification"""
    
    def setup_method(self):
        self.secret = "test_webhook_secret"
        self.security = WebhookSecurity(self.secret)
    
    def test_signature_verification_valid(self):
        """Test valid signature verification"""
        payload = b'{"test": "data"}'
        signature = "sha256=" + hmac.new(
            self.secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        result = self.security.verify_signature(payload, signature)
        assert result == True
    
    def test_signature_verification_invalid(self):
        """Test invalid signature verification"""
        payload = b'{"test": "data"}'
        signature = "sha256=invalid_signature"
        
        result = self.security.verify_signature(payload, signature)
        assert result == False
    
    def test_signature_verification_missing(self):
        """Test missing signature"""
        payload = b'{"test": "data"}'
        
        result = self.security.verify_signature(payload, "")
        assert result == False
        
        result = self.security.verify_signature(payload, None)
        assert result == False
    
    def test_signature_verification_wrong_format(self):
        """Test wrong signature format"""
        payload = b'{"test": "data"}'
        signature = "wrong_format"
        
        result = self.security.verify_signature(payload, signature)
        assert result == False
    
    def test_validation_stats(self):
        """Test validation statistics"""
        # Add some validation times
        self.security.validation_times = [0.1, 0.15, 0.12, 0.08]
        
        stats = self.security.get_validation_stats()
        
        assert stats["avg_time"] == pytest.approx(0.1125, rel=1e-3)
        assert stats["total_validations"] == 4
        assert stats["max_time"] == 0.15
        assert stats["min_time"] == 0.08
    
    def test_empty_validation_stats(self):
        """Test validation stats with no data"""
        stats = self.security.get_validation_stats()
        
        assert stats["avg_time"] == 0
        assert stats["total_validations"] == 0


class TestWebhookProcessor:
    """Test webhook event processing"""
    
    def setup_method(self):
        self.mock_orchestrator = Mock()
        self.secret = "test_webhook_secret"
        self.processor = WebhookProcessor(self.mock_orchestrator, self.secret)
    
    @pytest.mark.asyncio
    async def test_process_webhook_success(self):
        """Test successful webhook processing"""
        # Mock request
        mock_request = Mock(spec=Request)
        payload_data = {"action": "opened", "issue": {"number": 123}}
        payload_bytes = json.dumps(payload_data).encode('utf-8')
        
        # Generate valid signature
        signature = "sha256=" + hmac.new(
            self.secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        # Setup request mocks
        mock_request.headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "test-delivery-123"
        }
        mock_request.body = AsyncMock(return_value=payload_bytes)
        
        # Mock orchestrator response
        self.mock_orchestrator.handle_issue_event.return_value = {
            "task_id": "test-task-123",
            "success": True,
            "messages": []
        }
        
        # Process webhook
        result = await self.processor.process_webhook(mock_request)
        
        # Verify result
        assert result["status"] == "processed"
        assert result["delivery_id"] == "test-delivery-123"
        assert result["event_type"] == "issues"
        assert "processing_time" in result
        assert "security_time" in result
        assert result["result"]["action"] == "issue_processed"
    
    @pytest.mark.asyncio
    async def test_process_webhook_invalid_signature(self):
        """Test webhook processing with invalid signature"""
        # Mock request with invalid signature
        mock_request = Mock(spec=Request)
        payload_bytes = b'{"test": "data"}'
        
        mock_request.headers = {
            "X-Hub-Signature-256": "sha256=invalid_signature",
            "X-GitHub-Event": "issues"
        }
        mock_request.body = AsyncMock(return_value=payload_bytes)
        
        # Should raise HTTPException for invalid signature
        with pytest.raises(Exception):  # HTTPException in real context
            await self.processor.process_webhook(mock_request)
        
        # Should record error
        assert len(self.processor.error_counts) > 0
    
    @pytest.mark.asyncio
    async def test_process_webhook_missing_signature(self):
        """Test webhook processing with missing signature"""
        mock_request = Mock(spec=Request)
        payload_bytes = b'{"test": "data"}'
        
        mock_request.headers = {
            "X-GitHub-Event": "issues"
        }
        mock_request.body = AsyncMock(return_value=payload_bytes)
        
        # Should raise HTTPException for missing signature
        with pytest.raises(Exception):  # HTTPException in real context
            await self.processor.process_webhook(mock_request)
    
    @pytest.mark.asyncio
    async def test_process_webhook_latency_under_2s(self):
        """Test webhook processing under 2 seconds"""
        mock_request = Mock(spec=Request)
        payload_data = {"action": "opened", "issue": {"number": 123}}
        payload_bytes = json.dumps(payload_data).encode('utf-8')
        
        signature = "sha256=" + hmac.new(
            self.secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        mock_request.headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "test-delivery-123"
        }
        mock_request.body = AsyncMock(return_value=payload_bytes)
        
        self.mock_orchestrator.handle_issue_event.return_value = {
            "task_id": "test-task-123",
            "success": True
        }
        
        # Process webhook and measure time
        start_time = time.time()
        result = await self.processor.process_webhook(mock_request)
        processing_time = time.time() - start_time
        
        # Verify processing time is reasonable (should be much less than 2s)
        assert processing_time < 1.0, f"Processing took {processing_time}s, expected <1s"
        assert result["processing_time"] < 2.0, f"Processing time {result['processing_time']}s exceeded 2s limit"
    
    @pytest.mark.asyncio
    async def test_handle_issues_event(self):
        """Test issues event handling"""
        payload = {
            "action": "opened",
            "issue": {"number": 123, "title": "Test issue"},
            "repository": {"clone_url": "https://github.com/test/repo.git"}
        }
        
        # Mock successful orchestrator response
        self.mock_orchestrator.handle_issue_event.return_value = {
            "task_id": "test-123",
            "success": True,
            "messages": []
        }
        
        result = await self.processor._handle_issues_event(payload)
        
        assert result["action"] == "issue_processed"
        assert result["issue_number"] == 123
        assert "orchestrator_result" in result
    
    @pytest.mark.asyncio
    async def test_handle_pull_request_event(self):
        """Test pull request event handling"""
        payload = {
            "action": "opened",
            "pull_request": {"number": 456, "title": "Test PR"},
            "repository": {"clone_url": "https://github.com/test/repo.git"}
        }
        
        self.mock_orchestrator.handle_pull_request_event.return_value = {
            "task_id": "test-456",
            "success": True,
            "messages": []
        }
        
        result = await self.processor._handle_pull_request_event(payload)
        
        assert result["action"] == "pr_processed"
        assert result["pr_number"] == 456
        assert "orchestrator_result" in result
    
    @pytest.mark.asyncio
    async def test_handle_push_event(self):
        """Test push event handling"""
        payload = {
            "ref": "refs/heads/main",
            "repository": {"clone_url": "https://github.com/test/repo.git"},
            "commits": [{"id": "abc123", "message": "Test commit"}]
        }
        
        result = await self.processor._handle_push_event(payload)
        
        assert result["action"] == "push_logged"
        assert result["ref"] == "refs/heads/main"
        assert result["commit_count"] == 1
    
    @pytest.mark.asyncio
    async def test_handle_ping_event(self):
        """Test ping event handling"""
        payload = {"zen": "Non-blocking is better than blocking"}
        
        result = await self.processor._handle_ping_event(payload)
        
        assert result["message"] == "pong"
    
    @pytest.mark.asyncio
    async def test_security_blocking_issues_event(self):
        """Test security blocking in issues event"""
        payload = {
            "action": "opened",
            "issue": {"number": 123, "title": "Test issue"},
            "repository": {"clone_url": "https://malicious.com/repo.git"}  # Blocked domain
        }
        
        result = await self.processor._handle_issues_event(payload)
        
        assert result["action"] == "blocked"
        assert "error" in result
    
    def test_performance_stats(self):
        """Test performance statistics calculation"""
        # Add some processing times
        self.processor.processing_times = [0.5, 0.8, 0.6, 0.4]
        self.processor.event_counts = {"issues": 2, "pull_request": 2}
        self.processor.error_counts = {"ValueError": 1}
        
        stats = self.processor.get_performance_stats()
        
        assert stats["processing_times"]["avg"] == pytest.approx(0.575, rel=1e-3)
        assert stats["processing_times"]["max"] == 0.8
        assert stats["processing_times"]["min"] == 0.4
        assert stats["processing_times"]["total"] == 4
        
        assert stats["event_counts"]["issues"] == 2
        assert stats["event_counts"]["pull_request"] == 2
        assert stats["error_counts"]["ValueError"] == 1
        
        # Success rate: 4 successes / (4 successes + 1 error) = 0.8
        assert stats["success_rate"] == pytest.approx(0.8, rel=1e-3)
        assert stats["meets_latency_target"] == True  # 0.575s < 2s
        assert stats["meets_success_rate_target"] == False  # 80% < 99%


class TestSecurityGuardrails:
    """Test security guardrails integration"""
    
    def setup_method(self):
        # Reset global guardrails state for testing
        security_guardrails.audit_log.clear()
        security_guardrails.validation_times = []
    
    def test_file_access_validation(self):
        """Test file access validation"""
        # Test allowed file
        result = security_guardrails.validate_file_access("src/main.py", "read")
        assert result["valid"] == True
        
        # Test sensitive file
        result = security_guardrails.validate_file_access(".env", "read")
        assert result["valid"] == False
        assert "sensitive" in result["reason"].lower()
        
        # Test sensitive extension
        result = security_guardrails.validate_file_access("config.key", "read")
        assert result["valid"] == False
        assert "sensitive" in result["reason"].lower()
    
    def test_command_validation(self):
        """Test command validation"""
        # Test allowed command
        result = security_guardrails.validate_command("git status")
        assert result["valid"] == True
        
        # Test blocked command
        result = security_guardrails.validate_command("rm -rf /")
        assert result["valid"] == False
        assert "blocked" in result["reason"].lower()
        
        # Test dangerous arguments
        result = security_guardrails.validate_command("git reset --hard")
        assert result["valid"] == False
        assert "dangerous" in result["reason"].lower()
    
    def test_patch_validation(self):
        """Test patch validation"""
        # Test safe patch
        safe_patch = """
+++ src/main.py
@@ -1,3 +1,4 @@
 def hello():
+    print("Hello, World!")
     return "hello"
"""
        result = security_guardrails.validate_patch(safe_patch)
        assert result["valid"] == True
        
        # Test patch with dangerous code
        dangerous_patch = """
+++ src/main.py
@@ -1,3 +1,4 @@
 def hello():
+    eval("malicious code")
     return "hello"
"""
        result = security_guardrails.validate_patch(dangerous_patch)
        assert result["valid"] == False
        assert "dangerous" in result["issues"][0].lower()
        
        # Test patch with sensitive file
        sensitive_patch = """
+++ .env
@@ -0,0 +1 @@
+SECRET_KEY=super_secret
"""
        result = security_guardrails.validate_patch(sensitive_patch)
        assert result["valid"] == False
        assert "sensitive" in result["issues"][0].lower()
    
    def test_repository_access_validation(self):
        """Test repository access validation"""
        # Test GitHub repository
        result = security_guardrails.validate_repository_access(
            "https://github.com/user/repo.git", "read"
        )
        assert result["valid"] == True
        
        # Test non-GitHub repository
        result = security_guardrails.validate_repository_access(
            "https://gitlab.com/user/repo.git", "read"
        )
        assert result["valid"] == False
        assert "GitHub" in result["reason"]
        
        # Test invalid URL
        result = security_guardrails.validate_repository_access(
            "invalid-url", "read"
        )
        assert result["valid"] == False
        assert "format" in result["reason"].lower()
    
    def test_audit_logging(self):
        """Test audit logging functionality"""
        # Perform some actions
        security_guardrails.validate_file_access("src/main.py", "read")
        security_guardrails.validate_command("git status")
        security_guardrails.validate_patch("safe patch content")
        
        # Check audit log
        audit_log = security_guardrails.get_audit_log()
        assert len(audit_log) >= 3
        
        # Check log entries have required fields
        for entry in audit_log:
            assert "timestamp" in entry
            assert "action" in entry
            assert "details" in entry
    
    def test_security_stats(self):
        """Test security statistics"""
        # Add some audit entries
        security_guardrails.validate_file_access("src/main.py", "read")  # Should succeed
        security_guardrails.validate_file_access(".env", "read")  # Should fail
        
        stats = security_guardrails.get_security_stats()
        
        assert stats["total_actions"] >= 2
        assert stats["blocked_actions"] >= 1
        assert 0 <= stats["success_rate"] <= 1


class TestWebhookIntegration:
    """Test webhook integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_webhook_flow(self):
        """Test complete webhook processing flow"""
        mock_orchestrator = Mock()
        secret = "test_secret"
        processor = WebhookProcessor(mock_orchestrator, secret)
        
        # Mock successful orchestrator response
        mock_orchestrator.handle_issue_event.return_value = {
            "task_id": "integration-test-123",
            "success": True,
            "messages": [
                {"role": "planner", "content": "Plan created"},
                {"role": "coder", "content": "Code generated"},
                {"role": "reviewer", "content": "Review completed"}
            ],
            "performance": {"success_rate": 1.0}
        }
        
        # Create mock request
        mock_request = Mock(spec=Request)
        payload_data = {
            "action": "opened",
            "issue": {
                "number": 456,
                "title": "Integration test issue",
                "body": "This is a test issue for integration testing"
            },
            "repository": {
                "name": "test-repo",
                "clone_url": "https://github.com/test/test-repo.git"
            }
        }
        payload_bytes = json.dumps(payload_data).encode('utf-8')
        
        signature = "sha256=" + hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        mock_request.headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "integration-delivery-123"
        }
        mock_request.body = AsyncMock(return_value=payload_bytes)
        
        # Process webhook
        start_time = time.time()
        result = await processor.process_webhook(mock_request)
        total_time = time.time() - start_time
        
        # Verify complete flow
        assert result["status"] == "processed"
        assert result["delivery_id"] == "integration-delivery-123"
        assert result["event_type"] == "issues"
        assert result["processing_time"] < 2.0
        assert result["security_time"] < 0.1
        
        # Verify orchestrator was called
        mock_orchestrator.handle_issue_event.assert_called_once_with(payload_data)
        
        # Verify performance metrics
        perf_stats = processor.get_performance_stats()
        assert perf_stats["success_rate"] == 1.0
        assert perf_stats["meets_latency_target"] == True
        assert perf_stats["meets_success_rate_target"] == True
    
    @pytest.mark.asyncio
    async def test_webhook_success_rate_99_percent(self):
        """Test webhook success rate target of 99%"""
        mock_orchestrator = Mock()
        secret = "test_secret"
        processor = WebhookProcessor(mock_orchestrator, secret)
        
        # Mock successful responses
        mock_orchestrator.handle_issue_event.return_value = {
            "success": True,
            "messages": []
        }
        
        # Process multiple successful webhooks
        success_count = 0
        total_requests = 100
        
        for i in range(total_requests):
            try:
                mock_request = Mock(spec=Request)
                payload_data = {"action": "opened", "issue": {"number": i}}
                payload_bytes = json.dumps(payload_data).encode('utf-8')
                
                signature = "sha256=" + hmac.new(
                    secret.encode('utf-8'),
                    payload_bytes,
                    hashlib.sha256
                ).hexdigest()
                
                mock_request.headers = {
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "issues",
                    "X-GitHub-Delivery": f"delivery-{i}"
                }
                mock_request.body = AsyncMock(return_value=payload_bytes)
                
                result = await processor.process_webhook(mock_request)
                if result["status"] == "processed":
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Webhook {i} failed: {e}")
        
        success_rate = success_count / total_requests
        assert success_rate >= 0.99, f"Success rate {success_rate:.2%} below 99% target"
        
        # Verify processor stats
        stats = processor.get_performance_stats()
        assert stats["success_rate"] >= 0.99
        assert stats["meets_success_rate_target"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
