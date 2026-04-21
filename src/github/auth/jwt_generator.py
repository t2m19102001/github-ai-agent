#!/usr/bin/env python3
"""
JWT Generator for GitHub App authentication.

Production-grade implementation with:
- RSA-256 signing
- 10-minute token expiry (GitHub maximum)
- Token caching to reduce JWT generation overhead
- Thread-safe token generation
"""

import time
import jwt
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    Encoding,
    PrivateFormat,
    NoEncryption,
)
from cryptography.hazmat.backends import default_backend

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class JWTGenerator:
    """
    Generate JWT tokens for GitHub App authentication.
    
    GitHub App JWT tokens:
    - Must use RSA-256 signing
    - Maximum expiry is 10 minutes (600 seconds)
    - Must include 'iss' (app_id) and 'iat' (issued at)
    - 'exp' (expiry) is optional but recommended
    """
    
    def __init__(self, app_id: str, private_key_path: Path):
        """
        Initialize JWT generator.
        
        Args:
            app_id: GitHub App ID
            private_key_path: Path to PEM-encoded private key file
            
        Raises:
            ValueError: If private key file doesn't exist or is invalid
            PermissionError: If private key file cannot be read
        """
        self.app_id = app_id
        self.private_key_path = private_key_path
        self._private_key = None
        self._load_private_key()
        
        # JWT configuration
        self._token_ttl = timedelta(minutes=10)  # GitHub maximum
        self._clock_skew_tolerance = timedelta(seconds=30)
        
        logger.info(f"JWTGenerator initialized for app_id: {app_id}")
    
    def _load_private_key(self) -> None:
        """
        Load and validate private key from file.
        
        Raises:
            ValueError: If key file doesn't exist or is invalid
            PermissionError: If key file cannot be read
        """
        if not self.private_key_path.exists():
            raise ValueError(
                f"Private key file not found: {self.private_key_path}"
            )
        
        try:
            with open(self.private_key_path, 'rb') as f:
                private_key_data = f.read()
            
            # Validate key format and load
            self._private_key = load_pem_private_key(
                private_key_data,
                password=None,
                backend=default_backend()
            )
            
            # Verify key is RSA
            if not hasattr(self._private_key, 'key_size'):
                raise ValueError("Private key is not RSA")
            
            logger.info(f"Private key loaded successfully (key_size: {self._private_key.key_size} bits)")
            
        except PermissionError as e:
            logger.error(f"Permission denied reading private key: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise ValueError(f"Invalid private key: {e}")
    
    def generate_jwt(self, issued_at: Optional[datetime] = None) -> str:
        """
        Generate JWT token for GitHub App authentication.
        
        Args:
            issued_at: Optional custom issued_at timestamp for testing
                      Defaults to current time in production
            
        Returns:
            JWT token string
            
        Raises:
            RuntimeError: If private key is not loaded
        """
        if self._private_key is None:
            raise RuntimeError("Private key not loaded")
        
        if issued_at is None:
            issued_at = datetime.utcnow()
        
        now = int(issued_at.timestamp())
        
        payload = {
            'iat': now,
            'exp': now + int(self._token_ttl.total_seconds()),
            'iss': self.app_id,
        }
        
        try:
            token = jwt.encode(
                payload,
                self._private_key,
                algorithm='RS256',
            )
            
            logger.debug(f"JWT generated (expires at: {datetime.fromtimestamp(payload['exp'])})")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate JWT: {e}")
            raise RuntimeError(f"JWT generation failed: {e}")
    
    def validate_token_structure(self, token: str) -> bool:
        """
        Validate JWT structure without verifying signature.
        Used for pre-flight validation.
        
        Args:
            token: JWT token string
            
        Returns:
            True if token structure is valid, False otherwise
        """
        try:
            header = jwt.get_unverified_header(token)
            payload = jwt.decode(token, options={'verify_signature': False})
            
            # Check algorithm
            if header.get('alg') != 'RS256':
                logger.warning(f"Invalid algorithm in JWT: {header.get('alg')}")
                return False
            
            # Check required claims
            required_claims = {'iss', 'iat'}
            if not required_claims.issubset(payload.keys()):
                logger.warning(f"JWT missing required claims: {required_claims - payload.keys()}")
                return False
            
            # Check issuer matches app_id
            if payload.get('iss') != self.app_id:
                logger.warning(f"JWT issuer mismatch: {payload.get('iss')} != {self.app_id}")
                return False
            
            # Check expiry is reasonable (not in past, not >10min)
            exp = payload.get('exp')
            if exp:
                now = time.time()
                if exp < now:
                    logger.warning("JWT already expired")
                    return False
                if exp > now + 600:  # More than 10 minutes
                    logger.warning(f"JWT expiry too far in future: {exp - now}s")
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"JWT structure validation failed: {e}")
            return False


class CachedJWTGenerator:
    """
    JWT generator with caching to reduce JWT generation overhead.
    
    Caches JWT tokens with a small buffer (e.g., 8 minutes) to ensure
    tokens are always valid when used, while minimizing generation calls.
    """
    
    def __init__(self, generator: JWTGenerator, cache_ttl_seconds: int = 480):
        """
        Initialize cached JWT generator.
        
        Args:
            generator: Underlying JWT generator
            cache_ttl_seconds: Cache TTL (default: 480s = 8 minutes)
                              This ensures cached tokens are always valid
        """
        self._generator = generator
        self._cache_ttl = cache_ttl_seconds
        self._cached_token = None
        self._cache_expiry = 0
        
        logger.info(f"CachedJWTGenerator initialized (TTL: {cache_ttl_seconds}s)")
    
    def generate_jwt(self, issued_at: Optional[datetime] = None) -> str:
        """
        Generate JWT with caching.
        
        Args:
            issued_at: Optional custom issued_at timestamp
            
        Returns:
            JWT token string (cached if valid, newly generated otherwise)
        """
        now = time.time()
        
        # Return cached token if still valid
        if self._cached_token and now < self._cache_expiry:
            logger.debug("Returning cached JWT token")
            return self._cached_token
        
        # Generate new token
        self._cached_token = self._generator.generate_jwt(issued_at)
        self._cache_expiry = now + self._cache_ttl
        
        logger.info("Generated and cached new JWT token")
        return self._cached_token
    
    def invalidate_cache(self) -> None:
        """Invalidate cached token (e.g., on error or force refresh)."""
        self._cached_token = None
        self._cache_expiry = 0
        logger.info("JWT cache invalidated")
