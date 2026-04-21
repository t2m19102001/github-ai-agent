#!/usr/bin/env python3
"""
Concurrency tests for Installation Token Manager.
"""

import pytest
import asyncio
import time

from src.github.auth.installation_token_manager import InstallationToken, InstallationTokenManager


@pytest.mark.unit
class TestTokenManagerConcurrency:
    """Test token manager concurrency and single-flight pattern."""
    
    @pytest.fixture
    def mock_jwt_generator(self):
        """Mock JWT generator."""
        class MockJWTGenerator:
            def generate_jwt(self):
                return "mock_jwt_token"
        return MockJWTGenerator()
    
    @pytest.fixture
    async def token_manager(self, mock_jwt_generator):
        """Create token manager with mock dependencies."""
        manager = InstallationTokenManager(
            app_id="12345",
            jwt_generator=mock_jwt_generator,
            http_client=None,  # Will mock HTTP calls
            cache_ttl_seconds=3600,
        )
        # Mock the HTTP client to avoid actual API calls
        manager._http_client = AsyncMockHTTPClient()
        return manager
    
    @pytest.mark.asyncio
    async def test_concurrent_token_requests_single_flight(self, token_manager):
        """Test concurrent requests for same token use single-flight pattern."""
        installation_id = 12345
        
        # Simulate 10 concurrent requests for the same installation
        tasks = [token_manager.get_installation_token(installation_id) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should return tokens
        assert len(results) == 10
        assert all(isinstance(r, InstallationToken) for r in results)
        
        # Verify token generation was called only once (single-flight)
        assert token_manager._http_client.call_count == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_different_installations(self, token_manager):
        """Test concurrent requests for different installations."""
        installation_ids = [11111, 22222, 33333, 44444, 55555]
        
        # Request tokens for different installations concurrently
        tasks = [token_manager.get_installation_token(installation_id) for installation_id in installation_ids]
        results = await asyncio.gather(*tasks)
        
        # All should return tokens
        assert len(results) == 5
        assert all(isinstance(r, InstallationToken) for r in results)
        
        # Verify each installation was called
        assert token_manager._http_client.call_count == 5
    
    @pytest.mark.asyncio
    async def test_cache_hit_on_concurrent_requests(self, token_manager):
        """Test cache hit prevents token regeneration."""
        installation_id = 12345
        
        # First request - should generate token
        token1 = await token_manager.get_installation_token(installation_id)
        assert token_manager._http_client.call_count == 1
        
        # Second concurrent request - should use cache
        token2 = await token_manager.get_installation_token(installation_id)
        assert token_manager._http_client.call_count == 1  # Still 1
        
        # Tokens should match
        assert token1.token == token2.token
    
    @pytest.mark.asyncio
    async def test_force_refresh_concurrent(self, token_manager):
        """Test force refresh bypasses cache."""
        installation_id = 12345
        
        # First request
        token1 = await token_manager.get_installation_token(installation_id)
        assert token_manager._http_client.call_count == 1
        
        # Force refresh
        token2 = await token_manager.get_installation_token(installation_id, force_refresh=True)
        assert token_manager._http_client.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_concurrent(self, token_manager):
        """Test cache invalidation is thread-safe."""
        installation_id = 12345
        
        # Generate token
        token1 = await token_manager.get_installation_token(installation_id)
        
        # Invalidate cache
        await token_manager.invalidate_cache(installation_id)
        
        # Next request should generate new token
        token2 = await token_manager.get_installation_token(installation_id)
        assert token_manager._http_client.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_all(self, token_manager):
        """Test invalidating all caches."""
        installation_ids = [11111, 22222, 33333]
        
        # Generate tokens
        for installation_id in installation_ids:
            await token_manager.get_installation_token(installation_id)
        
        assert token_manager._http_client.call_count == 3
        
        # Invalidate all
        await token_manager.invalidate_cache()
        
        # All should regenerate
        for installation_id in installation_ids:
            await token_manager.get_installation_token(installation_id)
        
        assert token_manager._http_client.call_count == 6
    
    @pytest.mark.asyncio
    async def test_token_expiry_detection(self, token_manager):
        """Test token expiry detection and refresh."""
        installation_id = 12345
        
        # Create expired token
        expired_token = InstallationToken(
            token="expired_token",
            expires_at=time.time() - 3600,  # Expired 1 hour ago
            permissions={},
            repository_selection="all",
            installation_id=installation_id,
        )
        
        # Manually set expired token in cache
        token_manager._token_cache[installation_id] = (expired_token.token, time.time() - 7200)
        
        # Request should regenerate token
        token = await token_manager.get_installation_token(installation_id)
        assert token_manager._http_client.call_count == 1


class AsyncMockHTTPClient:
    """Mock async HTTP client for testing."""
    
    def __init__(self):
        self.call_count = 0
    
    async def post(self, url, headers):
        """Mock POST request."""
        self.call_count += 1
        await asyncio.sleep(0.01)  # Simulate network delay
        
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            
            def raise_for_status(self):
                pass
            
            def json(self):
                return {
                    "token": f"ghp_test_token_{self.call_count}",
                    "expires_at": "2024-04-21T00:00:00Z",
                    "permissions": {},
                    "repository_selection": "all",
                }
        
        return MockResponse()
    
    async def aclose(self):
        """Mock close."""
        pass
