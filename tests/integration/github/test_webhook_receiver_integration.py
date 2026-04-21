#!/usr/bin/env python3
"""
Integration tests for Webhook Receiver.
"""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.github.webhook.signature_verifier import SignatureVerifier
from src.github.webhook.deduplication import WebhookDeduplication
from src.github.webhook.webhook_receiver import WebhookReceiver


class TestWebhookReceiverIntegration:
    """Integration tests for webhook receiver."""
    
    @pytest.fixture
    def sample_payload(self):
        """Sample GitHub webhook payload."""
        return {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Test issue",
                "body": "Test body"
            },
            "repository": {
                "full_name": "test/repo",
                "id": 12345
            }
        }
    
    @pytest.fixture
    def webhook_secret(self):
        """Webhook secret."""
        return "webhook_secret_123"
    
    @pytest.fixture
    def signature_verifier(self, webhook_secret):
        """Signature verifier instance."""
        return SignatureVerifier(webhook_secret=webhook_secret)
    
    @pytest.fixture
    def deduplication(self):
        """Deduplication instance."""
        return WebhookDeduplication(
            redis_url="redis://localhost:6379/0",
            ttl_hours=24,
            fallback_to_db=True,
        )
    
    @pytest.fixture
    def webhook_receiver(self, signature_verifier, deduplication):
        """Webhook receiver instance."""
        return WebhookReceiver(
            signature_verifier=signature_verifier,
            deduplication=deduplication,
        )
    
    @pytest.mark.asyncio
    async def test_webhook_receiver_initialization(self, signature_verifier, deduplication):
        """Test webhook receiver initialization."""
        receiver = WebhookReceiver(
            signature_verifier=signature_verifier,
            deduplication=deduplication,
        )
        
        assert receiver.signature_verifier == signature_verifier
        assert receiver.deduplication == deduplication
    
    @pytest.mark.asyncio
    async def test_handle_webhook_valid_signature(self, webhook_receiver, sample_payload, webhook_secret):
        """Test webhook handling with valid signature."""
        # Compute signature
        payload_bytes = json.dumps(sample_payload).encode('utf-8')
        signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={signature}"
        
        # Create mock request
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/webhooks/github"
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-123",
            "X-Hub-Signature-256": signature_header,
        }
        
        # Mock call_next
        async def call_next(request):
            return MagicMock(status_code=202)
        
        # Handle webhook
        response = await webhook_receiver.handle_webhook(
            mock_request,
            x_github_event="issues",
            x_github_delivery="delivery-123",
            x_hub_signature_256=signature_header,
        )
        
        # Should return 202 Accepted
        assert response.status_code == 202
    
    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_signature(self, webhook_receiver, sample_payload):
        """Test webhook handling with invalid signature."""
        payload_bytes = json.dumps(sample_payload).encode('utf-8')
        
        # Create mock request with invalid signature
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/webhooks/github"
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-123",
            "X-Hub-Signature-256": "sha256=invalid_signature",
        }
        
        # Mock call_next (should not be called)
        async def call_next(request):
            return MagicMock(status_code=202)
        
        # Handle webhook
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await webhook_receiver.handle_webhook(
                mock_request,
                x_github_event="issues",
                x_github_delivery="delivery-123",
                x_hub_signature_256="sha256=invalid_signature",
            )
        
        assert exc_info.value.status_code == 401
        assert "Invalid signature" in exc_info.value.detail["error"]
    
    @pytest.mark.asyncio
    async def test_handle_webhook_duplicate(self, webhook_receiver, sample_payload, webhook_secret):
        """Test webhook handling with duplicate delivery."""
        payload_bytes = json.dumps(sample_payload).encode('utf-8')
        signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={signature}"
        
        # First call
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/webhooks/github"
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-123",
            "X-Hub-Signature-256": signature_header,
        }
        
        async def call_next(request):
            return MagicMock(status_code=202)
        
        # First call
        response1 = await webhook_receiver.handle_webhook(
            mock_request,
            x_github_event="issues",
            x_github_delivery="delivery-123",
            x_hub_signature_256=signature_header,
        )
        
        assert response1.status_code == 202
        
        # Second call (duplicate)
        response2 = await webhook_receiver.handle_webhook(
            mock_request,
            x_github_event="issues",
            x_github_delivery="delivery-123",
            x_hub_signature_256=signature_header,
        )
        
        # Should return 200 with already_processed status
        assert response2.status_code == 200
        assert response2.content["status"] == "already_processed"
