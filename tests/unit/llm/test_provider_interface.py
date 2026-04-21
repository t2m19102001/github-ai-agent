#!/usr/bin/env python3
"""
Unit tests for LLM Provider Interface.
"""

import pytest
from datetime import datetime

from src.llm.provider_interface import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    Message,
    ModelRole,
    LLMProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthenticationError,
)


class TestMessage:
    """Test Message entity."""
    
    def test_message_creation(self):
        """Test message creation."""
        message = Message(role=ModelRole.USER, content="Hello")
        
        assert message.role == ModelRole.USER
        assert message.content == "Hello"
    
    def test_message_with_metadata(self):
        """Test message with metadata."""
        message = Message(
            role=ModelRole.USER,
            content="Hello",
            metadata={"key": "value"}
        )
        
        assert message.metadata == {"key": "value"}


class TestLLMRequest:
    """Test LLMRequest entity."""
    
    def test_request_creation(self):
        """Test request creation."""
        request = LLMRequest(
            model="llama2-70b",
            messages=[
                Message(role=ModelRole.SYSTEM, content="You are helpful"),
                Message(role=ModelRole.USER, content="Hello"),
            ]
        )
        
        assert request.model == "llama2-70b"
        assert len(request.messages) == 2
        assert request.temperature == 0.7
    
    def test_request_with_custom_params(self):
        """Test request with custom parameters."""
        request = LLMRequest(
            model="llama2-70b",
            messages=[Message(role=ModelRole.USER, content="Hello")],
            temperature=0.5,
            max_tokens=1000,
            timeout=60,
        )
        
        assert request.temperature == 0.5
        assert request.max_tokens == 1000
        assert request.timeout == 60


class TestLLMResponse:
    """Test LLMResponse entity."""
    
    def test_response_creation(self):
        """Test response creation."""
        response = LLMResponse(
            content="Hello!",
            model="llama2-70b",
            provider="groq",
            finish_reason="stop",
            tokens_used=100,
            prompt_tokens=50,
            completion_tokens=50,
            latency_ms=500.0,
        )
        
        assert response.content == "Hello!"
        assert response.model == "llama2-70b"
        assert response.provider == "groq"
        assert response.tokens_used == 100
    
    def test_response_to_dict(self):
        """Test response serialization."""
        response = LLMResponse(
            content="Hello!",
            model="llama2-70b",
            provider="groq",
            finish_reason="stop",
            tokens_used=100,
            prompt_tokens=50,
            completion_tokens=50,
            latency_ms=500.0,
        )
        
        response_dict = response.to_dict()
        
        assert response_dict["content"] == "Hello!"
        assert response_dict["tokens_used"] == 100
        assert response_dict["latency_ms"] == 500.0


class TestProviderErrors:
    """Test provider error types."""
    
    def test_provider_timeout_error(self):
        """Test ProviderTimeoutError."""
        error = ProviderTimeoutError("Request timed out")
        
        assert isinstance(error, LLMProviderError)
        assert "timed out" in str(error)
    
    def test_provider_rate_limit_error(self):
        """Test ProviderRateLimitError."""
        error = ProviderRateLimitError("Rate limit exceeded", retry_after=60)
        
        assert isinstance(error, LLMProviderError)
        assert error.retry_after == 60
    
    def test_provider_authentication_error(self):
        """Test ProviderAuthenticationError."""
        error = ProviderAuthenticationError("Authentication failed")
        
        assert isinstance(error, LLMProviderError)
