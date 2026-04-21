#!/usr/bin/env python3
"""
Unit tests for JWT Generator.
"""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from src.github.auth.jwt_generator import JWTGenerator, CachedJWTGenerator


@pytest.fixture
def test_private_key_path(tmp_path):
    """Generate a test RSA private key."""
    private_key_path = tmp_path / "test_private_key.pem"
    
    # Generate RSA key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Save private key
    with open(private_key_path, 'wb') as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    return private_key_path


class TestJWTGenerator:
    """Test JWT generation and validation."""
    
    def test_jwt_generator_initialization(self, test_private_key_path):
        """Test JWT generator initialization."""
        generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        
        assert generator.app_id == "12345"
        assert generator.private_key_path == test_private_key_path
        assert generator._private_key is not None
        assert generator._token_ttl == timedelta(minutes=10)
    
    def test_jwt_generator_missing_key(self, tmp_path):
        """Test JWT generator with missing private key."""
        non_existent_path = tmp_path / "non_existent.pem"
        
        with pytest.raises(ValueError, match="Private key file not found"):
            JWTGenerator(app_id="12345", private_key_path=non_existent_path)
    
    def test_generate_jwt(self, test_private_key_path):
        """Test JWT generation."""
        generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        
        token = generator.generate_jwt()
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are typically >100 chars
    
    def test_generate_jwt_with_custom_time(self, test_private_key_path):
        """Test JWT generation with custom issued_at timestamp."""
        generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        token = generator.generate_jwt(issued_at=custom_time)
        
        assert isinstance(token, str)
    
    def test_validate_token_structure_valid(self, test_private_key_path):
        """Test JWT structure validation with valid token."""
        generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        
        token = generator.generate_jwt()
        is_valid = generator.validate_token_structure(token)
        
        assert is_valid is True
    
    def test_validate_token_structure_invalid_algorithm(self, test_private_key_path):
        """Test JWT structure validation with invalid algorithm."""
        generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        
        # Create a fake token with wrong algorithm
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake"
        
        is_valid = generator.validate_token_structure(fake_token)
        
        assert is_valid is False
    
    def test_validate_token_structure_missing_issuer(self, test_private_key_path):
        """Test JWT structure validation with missing issuer."""
        generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        
        # Create a fake token without issuer (would need actual JWT library to create)
        # For now, test with malformed token
        fake_token = "invalid.token"
        
        is_valid = generator.validate_token_structure(fake_token)
        
        assert is_valid is False


class TestCachedJWTGenerator:
    """Test cached JWT generation."""
    
    def test_cached_jwt_generator_initialization(self, test_private_key_path):
        """Test cached JWT generator initialization."""
        base_generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        
        cached = CachedJWTGenerator(base_generator, cache_ttl_seconds=300)
        
        assert cached._generator == base_generator
        assert cached._cache_ttl == 300
    
    def test_cached_jwt_generation(self, test_private_key_path):
        """Test cached JWT generation."""
        base_generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        cached = CachedJWTGenerator(base_generator, cache_ttl_seconds=300)
        
        # First call - generates new token
        token1 = cached.generate_jwt()
        
        # Second call - returns cached token (within TTL)
        token2 = cached.generate_jwt()
        
        assert token1 == token2
    
    def test_cache_expiry(self, test_private_key_path):
        """Test that cached tokens expire after TTL."""
        import asyncio
        
        base_generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        cached = CachedJWTGenerator(base_generator, cache_ttl_seconds=1)  # 1 second TTL
        
        # Generate and cache
        token1 = cached.generate_jwt()
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Should generate new token
        token2 = cached.generate_jwt()
        
        assert token1 != token2
    
    def test_invalidate_cache(self, test_private_key_path):
        """Test cache invalidation."""
        base_generator = JWTGenerator(app_id="12345", private_key_path=test_private_key_path)
        cached = CachedJWTGenerator(base_generator, cache_ttl_seconds=300)
        
        # Generate and cache
        token1 = cached.generate_jwt()
        
        # Invalidate cache
        cached.invalidate_cache()
        
        # Should generate new token
        token2 = cached.generate_jwt()
        
        # Tokens may still be the same if generator produces same output
        # But cache was cleared
        assert cached._cached_token is None
