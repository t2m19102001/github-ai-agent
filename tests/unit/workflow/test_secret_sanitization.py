#!/usr/bin/env python3
"""
Tests for secret sanitization in logs.
"""

import pytest

from src.workflow.orchestrator import sanitize_for_logging


@pytest.mark.unit
class TestSecretSanitization:
    """Test secret sanitization prevents leaks in logs."""
    
    def test_sanitize_redacts_token(self):
        """Test token is redacted."""
        data = {"token": "ghp_secret_token_12345"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["token"] == "[REDACTED]"
    
    def test_sanitize_redacts_password(self):
        """Test password is redacted."""
        data = {"password": "my_secret_password"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["password"] == "[REDACTED]"
    
    def test_sanitize_redacts_secret(self):
        """Test secret is redacted."""
        data = {"secret": "my_secret_value"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["secret"] == "[REDACTED]"
    
    def test_sanitize_redacts_api_key(self):
        """Test api_key is redacted."""
        data = {"api_key": "sk_live_12345"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["api_key"] == "[REDACTED]"
    
    def test_sanitize_redacts_private_key(self):
        """Test private_key is redacted."""
        data = {"private_key": "-----BEGIN PRIVATE KEY-----"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["private_key"] == "[REDACTED]"
    
    def test_sanitize_redacts_credential(self):
        """Test credential is redacted."""
        data = {"credential": "user:password"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["credential"] == "[REDACTED]"
    
    def test_sanitize_redacts_auth(self):
        """Test auth is redacted."""
        data = {"auth": "Bearer token123"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["auth"] == "[REDACTED]"
    
    def test_sanitize_redacts_authorization(self):
        """Test authorization is redacted."""
        data = {"authorization": "Bearer token123"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["authorization"] == "[REDACTED]"
    
    def test_sanitize_redacts_bearer(self):
        """Test bearer is redacted."""
        data = {"bearer": "token123"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["bearer"] == "[REDACTED]"
    
    def test_sanitize_redacts_jwt(self):
        """Test jwt is redacted."""
        data = {"jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["jwt"] == "[REDACTED]"
    
    def test_sanitize_redacts_github_token(self):
        """Test github_token is redacted."""
        data = {"github_token": "ghp_12345"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["github_token"] == "[REDACTED]"
    
    def test_sanitize_redacts_webhook_secret(self):
        """Test webhook_secret is redacted."""
        data = {"webhook_secret": "secret123"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["webhook_secret"] == "[REDACTED]"
    
    def test_sanitize_redacts_signature(self):
        """Test signature is redacted."""
        data = {"signature": "sha256=abc123"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["signature"] == "[REDACTED]"
    
    def test_sanitize_case_insensitive(self):
        """Test key matching is case-insensitive."""
        data = {"ToKeN": "secret_value"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["ToKeN"] == "[REDACTED]"
    
    def test_sanitize_nested_dicts(self):
        """Test nested dictionaries are sanitized."""
        data = {
            "user": "john",
            "credentials": {
                "token": "secret_token",
                "password": "secret_pass"
            }
        }
        sanitized = sanitize_for_logging(data)
        assert sanitized["user"] == "john"
        assert sanitized["credentials"]["token"] == "[REDACTED]"
        assert sanitized["credentials"]["password"] == "[REDACTED]"
    
    def test_sanitize_truncates_long_strings(self):
        """Test long strings are truncated."""
        data = {"long_string": "x" * 200}
        sanitized = sanitize_for_logging(data)
        assert len(sanitized["long_string"]) == 113  # 100 + "...[truncated]"
        assert sanitized["long_string"].endswith("...[truncated]")
    
    def test_sanitize_preserves_short_strings(self):
        """Test short strings are preserved."""
        data = {"short_string": "hello"}
        sanitized = sanitize_for_logging(data)
        assert sanitized["short_string"] == "hello"
    
    def test_sanitize_preserves_non_sensitive_data(self):
        """Test non-sensitive data is preserved."""
        data = {
            "user_id": 123,
            "username": "john",
            "email": "john@example.com",
            "status": "active"
        }
        sanitized = sanitize_for_logging(data)
        assert sanitized["user_id"] == 123
        assert sanitized["username"] == "john"
        assert sanitized["email"] == "john@example.com"
        assert sanitized["status"] == "active"
    
    def test_sanitize_handles_empty_dict(self):
        """Test empty dict is handled."""
        data = {}
        sanitized = sanitize_for_logging(data)
        assert sanitized == {}
    
    def test_sanitize_handles_none(self):
        """Test None is handled."""
        sanitized = sanitize_for_logging(None)
        assert sanitized is None
    
    def test_sanitize_handles_string(self):
        """Test string is handled."""
        sanitized = sanitize_for_logging("test")
        assert sanitized == "test"
    
    def test_sanitize_handles_int(self):
        """Test int is handled."""
        sanitized = sanitize_for_logging(123)
        assert sanitized == 123
    
    def test_sanitize_mixed_sensitive_safe_data(self):
        """Test mixed sensitive and safe data."""
        data = {
            "user": "john",
            "token": "secret_token",
            "count": 42,
            "password": "secret_pass",
            "message": "hello world"
        }
        sanitized = sanitize_for_logging(data)
        assert sanitized["user"] == "john"
        assert sanitized["token"] == "[REDACTED]"
        assert sanitized["count"] == 42
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["message"] == "hello world"
    
    def test_sanitize_deeply_nested(self):
        """Test deeply nested structures are sanitized."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "token": "deep_secret",
                        "name": "test"
                    }
                }
            }
        }
        sanitized = sanitize_for_logging(data)
        assert sanitized["level1"]["level2"]["level3"]["token"] == "[REDACTED]"
        assert sanitized["level1"]["level2"]["level3"]["name"] == "test"
    
    def test_sanitize_list_values(self):
        """Test list values are not recursively sanitized (only dicts)."""
        data = {"items": ["token1", "token2"]}
        sanitized = sanitize_for_logging(data)
        # Lists are not recursively sanitized by current implementation
        assert sanitized["items"] == ["token1", "token2"]
    
    def test_sanitize_multiple_secrets(self):
        """Test multiple secrets are all redacted."""
        data = {
            "token": "token123",
            "password": "pass123",
            "secret": "secret123",
            "api_key": "key123"
        }
        sanitized = sanitize_for_logging(data)
        assert all(value == "[REDACTED]" for value in sanitized.values())
