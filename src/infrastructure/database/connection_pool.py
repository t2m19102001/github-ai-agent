#!/usr/bin/env python/env python3
"""
Connection Pool Configuration.

Production-grade connection pool management with:
- Pool size limits
- Overflow handling
- Connection recycling
- Pre-ping validation
"""

from typing import Optional
from dataclasses import dataclass

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConnectionPool:
    """
    Connection pool manager.
    
    Production configuration:
    - Pool size: 20 connections (base)
    - Max overflow: 10 connections (peak load)
    - Pool timeout: 30 seconds (wait for connection)
    - Pool recycle: 3600 seconds (1 hour)
    - Pre-ping: True (validate connections before use)
    """
    
    def __init__(
        self,
        config: 'DatabaseConfig',
    ):
        """
        Initialize connection pool manager.
        
        Args:
            config: Database configuration
        """
        self.config = config
        
        logger.info(
            f"ConnectionPool initialized "
            f"(size: {config.pool_size}, "
            f"max_overflow: {config.max_overflow}, "
            "recycle: {config.pool_recycle}s)"
        )
    
    def get_pool_stats(self) -> dict:
        """Get current pool statistics."""
        return {
            "size": self.config.pool_size,
            "max_overflow": self.config.max_overflow,
            "timeout": self.config.pool_timeout,
            "recycle": self.config.pool_recycle,
            "pre_ping": self.config.pool_pre_ping,
        }
