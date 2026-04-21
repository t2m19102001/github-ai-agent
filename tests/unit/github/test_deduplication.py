#!/usr/bin/env python3
"""
Unit tests for Webhook Deduplication.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.github.webhook.deduplication import WebhookDeduplication, DatabaseDeduplication


class TestWebhookDeduplication:
    """Test webhook deduplication."""
    
    @pytest.fixture
    def deduplication(self):
        """Create deduplication instance (without Redis for unit tests)."""
        return WebhookDeduplication(
            redis_url="redis://localhost:6379/0",
            ttl_hours=24,
            fallback_to_db=True,
        )
    
    def test_deduplication_initialization(self):
        """Test deduplication initialization."""
        dedup = WebhookDeduplication(redis_url="redis://localhost:6379/0")
        
        assert dedup.redis_url == "redis://localhost:6379/0"
        assert dedup.ttl.total_seconds() == 86400  # 24 hours
    
    def test_deduplication_without_redis(self):
        """Test deduplication without Redis (uses database fallback)."""
        dedup = WebhookDeduplication(
            redis_url="redis://localhost:6379/0",
            fallback_to_db=True,
        )
        
        # Initialize should handle missing Redis
        # (would need to mock redis module availability)
    
    @pytest.mark.asyncio
    async def test_check_and_mark_first_time(self, deduplication):
        """Test first-time webhook processing (not duplicate)."""
        # Mock database fallback
        deduplication._db_fallback = DatabaseDeduplication()
        
        result = await deduplication.check_and_mark(
            delivery_id="delivery-123",
            event_type="issues",
            payload=b'{"action":"opened"}',
        )
        
        is_duplicate, cached_response = result
        assert is_duplicate is False
        assert cached_response is None
    
    @pytest.mark.asyncio
    async def test_check_and_mark_duplicate(self, deduplication):
        """Test duplicate webhook processing."""
        deduplication._db_fallback = DatabaseDeduplication()
        
        # First call
        await deduplication.check_and_mark(
            delivery_id="delivery-123",
            event_type="issues",
            payload=b'{"action":"opened"}',
        )
        
        # Second call (duplicate)
        result = await deduplication.check_and_mark(
            delivery_id="delivery-123",
            event_type="issues",
            payload=b'{"action":"opened"}',
        )
        
        is_duplicate, cached_response = result
        assert is_duplicate is True
        assert cached_response == "in-memory-cached"


class TestDatabaseDeduplication:
    """Test database deduplication fallback."""
    
    def test_database_deduplication_initialization(self):
        """Test database deduplication initialization."""
        db_dedup = DatabaseDeduplication()
        
        assert db_dedup is not None
    
    @pytest.mark.asyncio
    async def test_database_deduplication_first_time(self):
        """Test first-time processing with database fallback."""
        db_dedup = DatabaseDeduplication()
        
        result = await db_dedup.check_and_mark(
            delivery_id="delivery-123",
            event_type="issues",
            payload=b'{"action":"opened"}',
        )
        
        is_duplicate, cached_response = result
        assert is_duplicate is False
        assert cached_response is None
    
    @pytest.mark.asyncio
    async def test_database_deduplication_duplicate(self):
        """Test duplicate detection with database fallback."""
        db_dedup = DatabaseDeduplication()
        
        # First call
        await db_dedup.check_and_mark(
            delivery_id="delivery-123",
            event_type="issues",
            payload=b'{"action":"opened"}',
        )
        
        # Second call
        result = await db_dedup.check_and_mark(
            delivery_id="delivery-123",
            event_type="issues",
            payload=b'{"action":"opened"}',
        )
        
        is_duplicate, cached_response = result
        assert is_duplicate is True
        assert cached_response == "in-memory-cached"
