#!/usr/bin/env python3
"""
Idempotency Manager.

Production-grade implementation with:
- Request deduplication
- Idempotency keys
- TTL management
"""

import json
from typing import Optional, Tuple
from datetime import datetime, timedelta

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class IdempotencyManager:
    """
    Idempotency manager.
    
    Ensures idempotent workflow execution.
    """
    
    def __init__(self, redis_client, ttl_hours: int = 24):
        """
        Initialize idempotency manager.
        
        Args:
            redis_client: Redis client
            ttl_hours: Time to live in hours
        """
        self.redis_client = redis_client
        self.ttl = timedelta(hours=ttl_hours)
        
        logger.info(f"IdempotencyManager initialized (TTL: {ttl_hours}h)")
    
    async def is_duplicate(self, workflow_id: str) -> bool:
        """
        Check if workflow is a duplicate.
        
        DEPRECATED: Use check_and_mark_atomic instead to avoid race conditions.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            True if duplicate, False otherwise
        """
        key = f"idempotency:{workflow_id}"
        
        try:
            exists = await self.redis_client.exists(key)
            return exists > 0
        except Exception as e:
            logger.error(f"Idempotency check failed: {e}")
            return False
    
    async def check_and_mark_atomic(self, workflow_id: str, result: dict = None) -> Tuple[bool, Optional[dict]]:
        """
        Atomically check if workflow is duplicate and mark as processed if not.
        
        This prevents race conditions between check and mark operations.
        
        Args:
            workflow_id: Workflow ID
            result: Result to store if not duplicate
            
        Returns:
            (is_duplicate, cached_result) tuple
        """
        key = f"idempotency:{workflow_id}"
        
        try:
            # Try to set key with NX (only if not exists) - atomic operation
            value = json.dumps(result) if result else "1"
            set_result = await self.redis_client.set(
                key,
                value,
                nx=True,  # Only set if not exists
                ex=int(self.ttl.total_seconds())
            )
            
            if set_result is None:
                # Key already exists - it's a duplicate
                cached_data = await self.redis_client.get(key)
                cached_result = json.loads(cached_data) if cached_data else None
                logger.info(f"Duplicate workflow detected: {workflow_id}")
                return True, cached_result
            
            # Successfully marked as processed
            logger.info(f"Marked workflow as processed (atomic): {workflow_id}")
            return False, None
            
        except Exception as e:
            logger.error(f"Atomic idempotency check failed: {e}")
            # Fail open - allow processing if deduplication fails
            return False, None
    
    async def mark_processed(self, workflow_id: str, result: dict):
        """
        Mark workflow as processed.
        
        DEPRECATED: Use check_and_mark_atomic instead.
        
        Args:
            workflow_id: Workflow ID
            result: Workflow result
        """
        key = f"idempotency:{workflow_id}"
        
        try:
            # Store result with TTL
            await self.redis_client.setex(
                key,
                int(self.ttl.total_seconds()),
                json.dumps(result)
            )
            
            logger.info(f"Marked workflow as processed: {workflow_id}")
            
        except Exception as e:
            logger.error(f"Failed to mark workflow as processed: {e}")
    
    async def get_result(self, workflow_id: str) -> Optional[dict]:
        """
        Get cached result for workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Cached result or None
        """
        key = f"idempotency:{workflow_id}"
        
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached result: {e}")
            return None
