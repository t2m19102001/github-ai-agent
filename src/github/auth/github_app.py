#!/usr/bin/env python3
"""
GitHub App Authentication Manager.

Production-grade implementation with:
- JWT generation
- Installation token management
- Secure private key handling
- Token caching
- Error handling and retry
"""

from pathlib import Path
from typing import Optional

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .jwt_generator import JWTGenerator, CachedJWTGenerator
from .installation_token_manager import InstallationTokenManager

logger = get_logger(__name__)


class GitHubAppAuth:
    """
    GitHub App authentication manager.
    
    Provides:
    - JWT token generation for app authentication
    - Installation token generation for repository access
    - Token caching to minimize API calls
    - Secure private key management
    """
    
    def __init__(
        self,
        app_id: str,
        private_key_path: Path,
        http_client=None,
        enable_caching: bool = True,
    ):
        """
        Initialize GitHub App authentication.
        
        Args:
            app_id: GitHub App ID
            private_key_path: Path to PEM-encoded private key
            http_client: Optional httpx.AsyncClient for testing
            enable_caching: Enable JWT and token caching (recommended)
            
        Raises:
            ValueError: If private key is invalid
        """
        self.app_id = app_id
        self.private_key_path = private_key_path
        self.enable_caching = enable_caching
        
        # Initialize JWT generator
        jwt_generator = JWTGenerator(app_id, private_key_path)
        
        if enable_caching:
            self._jwt_generator = CachedJWTGenerator(jwt_generator)
        else:
            self._jwt_generator = jwt_generator
        
        # Initialize installation token manager
        self._token_manager = InstallationTokenManager(
            app_id=app_id,
            jwt_generator=self._jwt_generator,
            http_client=http_client,
        )
        
        logger.info(f"GitHubAppAuth initialized (app_id: {app_id}, caching: {enable_caching})")
    
    def generate_jwt(self, issued_at: Optional = None) -> str:
        """
        Generate JWT token for GitHub App authentication.
        
        Args:
            issued_at: Optional custom issued_at timestamp (testing only)
            
        Returns:
            JWT token string
            
        Raises:
            RuntimeError: If JWT generation fails
        """
        return self._jwt_generator.generate_jwt(issued_at)
    
    async def get_installation_token(
        self,
        installation_id: int,
        force_refresh: bool = False
    ):
        """
        Get installation token for repository access.
        
        Args:
            installation_id: GitHub installation ID
            force_refresh: Force token refresh even if cached
            
        Returns:
            InstallationToken instance
            
        Raises:
            RuntimeError: If token generation fails
        """
        return await self._token_manager.get_installation_token(
            installation_id,
            force_refresh
        )
    
    def invalidate_jwt_cache(self) -> None:
        """Invalidate JWT cache."""
        if self.enable_caching:
            self._jwt_generator.invalidate_cache()
    
    def invalidate_token_cache(self, installation_id: Optional[int] = None) -> None:
        """
        Invalidate installation token cache.
        
        Args:
            installation_id: Specific installation ID to invalidate,
                          or None to invalidate all
        """
        self._token_manager.invalidate_cache(installation_id)
    
    async def close(self) -> None:
        """Close resources."""
        await self._token_manager.close()
        logger.info("GitHubAppAuth closed")
