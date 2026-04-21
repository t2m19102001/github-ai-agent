#!/usr/bin/env python3
"""
Integration tests for GitHub App Authentication.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from src.github.auth.github_app import GitHubAppAuth
from src.github.auth.jwt_generator import JWTGenerator, CachedJWTGenerator


class TestGitHubAppAuthIntegration:
    """Integration tests for GitHub App authentication."""
    
    @pytest.fixture
    def test_key_path(self, tmp_path):
        """Generate a test RSA private key."""
        private_key_path = tmp_path / "test_key.pem"
        
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        with open(private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        return private_key_path
    
    @pytest.fixture
    def github_app_auth(self, test_key_path):
        """Create GitHub App auth instance."""
        return GitHubAppAuth(
            app_id="12345",
            private_key_path=test_key_path,
            enable_caching=True,
        )
    
    def test_github_app_auth_initialization(self, github_app_auth):
        """Test GitHub App auth initialization."""
        assert github_app_auth.app_id == "12345"
        assert github_app_auth.private_key_path == test_key_path
        assert github_app_auth.enable_caching is True
        assert github_app_auth._jwt_generator is not None
        assert github_app_auth._token_manager is not None
    
    def test_generate_jwt(self, github_app_auth):
        """Test JWT generation."""
        token = github_app_auth.generate_jwt()
        
        assert isinstance(token, str)
        assert len(token) > 100
    
    def test_jwt_caching(self, github_app_auth):
        """Test JWT caching."""
        token1 = github_app_auth.generate_jwt()
        token2 = github_app_auth.generate_jwt()
        
        # With caching, should return same token within TTL
        assert token1 == token2
    
    def test_invalidate_jwt_cache(self, github_app_auth):
        """Test JWT cache invalidation."""
        token1 = github_app_auth.generate_jwt()
        
        github_app_auth.invalidate_jwt_cache()
        
        token2 = github_app_auth.generate_jwt()
        
        # Tokens may be different after invalidation
        assert github_app_auth._jwt_generator._cached_token is None


class TestJWTGeneratorIntegration:
    """Integration tests for JWT generator."""
    
    @pytest.fixture
    def test_key_path(self, tmp_path):
        """Generate a test RSA private key."""
        private_key_path = tmp_path / "test_key.pem"
        
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        with open(private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        return private_key_path
    
    def test_jwt_with_real_key(self, test_key_path):
        """Test JWT generation with real RSA key."""
        generator = JWTGenerator(app_id="12345", private_key_path=test_key_path)
        
        token = generator.generate_jwt()
        
        assert isinstance(token, str)
        
        # Validate token structure
        is_valid = generator.validate_token_structure(token)
        assert is_valid is True
    
    def test_jwt_expiry(self, test_key_path):
        """Test JWT expiry time."""
        generator = JWTGenerator(app_id="12345", private_key_path=test_key_path)
        
        token = generator.generate_jwt()
        
        # Parse token to check expiry
        import jwt
        payload = jwt.decode(token, options={'verify_signature': False})
        
        # Check expiry is approximately 10 minutes from now
        exp = datetime.fromtimestamp(payload['exp'])
        now = datetime.utcnow()
        
        # Should be approximately 10 minutes (allow 1 second tolerance)
        expected_expiry = now + timedelta(minutes=10)
        time_diff = abs((exp - expected_expiry).total_seconds())
        
        assert time_diff < 2.0  # Within 2 seconds tolerance
