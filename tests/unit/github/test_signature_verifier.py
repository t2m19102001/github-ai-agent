#!/usr/bin/env python3
"""
Unit tests for Signature Verifier.
"""

import pytest
import hmac
import hashlib

from src.github.webhook.signature_verifier import SignatureVerifier, VerificationResult


class TestSignatureVerifier:
    """Test webhook signature verification."""
    
    @pytest.fixture
    def sample_payload(self):
        """Sample webhook payload."""
        return b'{"action":"opened","issue":{"number":123}}'
    
    @pytest.fixture
    def sample_secret(self):
        """Sample webhook secret."""
        return "webhook_secret_123"
    
    @pytest.fixture
    def signature_verifier(self, sample_secret):
        """Signature verifier instance."""
        return SignatureVerifier(webhook_secret=sample_secret, require_signature=True)
    
    def test_signature_verifier_initialization(self, sample_secret):
        """Test signature verifier initialization."""
        verifier = SignatureVerifier(webhook_secret=sample_secret)
        
        assert verifier.webhook_secret == sample_secret
        assert verifier.require_signature is True
    
    def test_signature_verifier_no_secret_without_require(self):
        """Test signature verifier without secret when not required."""
        verifier = SignatureVerifier(webhook_secret="", require_signature=False)
        
        assert verifier.webhook_secret == ""
        assert verifier.require_signature is False
    
    def test_signature_verifier_no_secret_with_require(self):
        """Test signature verifier without secret when required."""
        with pytest.raises(ValueError, match="webhook_secret is required"):
            SignatureVerifier(webhook_secret="", require_signature=True)
    
    def test_verify_valid_signature(self, signature_verifier, sample_payload, sample_secret):
        """Test verification with valid signature."""
        # Compute expected signature
        expected_signature = hmac.new(
            sample_secret.encode('utf-8'),
            sample_payload,
            hashlib.sha256
        ).hexdigest()
        
        signature_header = f"sha256={expected_signature}"
        
        result = signature_verifier.verify(sample_payload, signature_header)
        
        assert result.valid is True
        assert result.error is None
    
    def test_verify_invalid_signature(self, signature_verifier, sample_payload):
        """Test verification with invalid signature."""
        signature_header = "sha256=invalid_signature"
        
        result = signature_verifier.verify(sample_payload, signature_header)
        
        assert result.valid is False
        assert result.error == "Signature mismatch"
    
    def test_verify_missing_signature(self, signature_verifier, sample_payload):
        """Test verification with missing signature."""
        result = signature_verifier.verify(sample_payload, "")
        
        assert result.valid is False
        assert result.error == "Missing X-Hub-Signature-256 header"
    
    def test_verify_invalid_format(self, signature_verifier, sample_payload):
        """Test verification with invalid signature format."""
        signature_header = "invalid_format"
        
        result = signature_verifier.verify(sample_payload, signature_header)
        
        assert result.valid is False
        assert "Invalid signature format" in result.error
    
    def test_validate_header_format_valid(self, signature_verifier, sample_payload):
        """Test header format validation with valid format."""
        # Compute valid signature
        sample_secret = signature_verifier.webhook_secret
        expected_signature = hmac.new(
            sample_secret.encode('utf-8'),
            sample_payload,
            hashlib.sha256
        ).hexdigest()
        
        signature_header = f"sha256={expected_signature}"
        
        is_valid = signature_verifier.validate_header_format(signature_header)
        
        assert is_valid is True
    
    def test_validate_header_format_missing_prefix(self, signature_verifier):
        """Test header format validation without sha256= prefix."""
        signature_header = "a" * 64  # 64 hex chars but no prefix
        
        is_valid = signature_verifier.validate_header_format(signature_header)
        
        assert is_valid is False
    
    def test_validate_header_format_wrong_length(self, signature_verifier):
        """Test header format validation with wrong length."""
        signature_header = "sha256=" + "a" * 63  # 63 chars instead of 64
        
        is_valid = signature_verifier.validate_header_format(signature_header)
        
        assert is_valid is False
    
    def test_validate_header_format_invalid_hex(self, signature_verifier):
        """Test header format validation with invalid hex."""
        signature_header = "sha256=" + "g" * 64  # Invalid hex
        
        is_valid = signature_verifier.validate_header_format(signature_header)
        
        assert is_valid is False
    
    def test_compute_signature(self, signature_verifier, sample_payload):
        """Test signature computation."""
        signature = signature_verifier._compute_signature(sample_payload)
        
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA-256 = 64 hex chars
        assert all(c in '0123456789abcdef' for c in signature)
