#!/usr/bin/env python3
"""
Production Database Configuration.

Production-grade configuration with:
- Connection pooling
- Statement timeout
- Lock timeout
- Transaction isolation level
- Connection recycling
"""

from typing import Optional
from dataclasses import dataclass

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DatabaseConfig:
    """
    Production database configuration.
    
    Production values:
    - Pool size: 20 connections
    - Max overflow: 10 connections
    - Pool timeout: 30 seconds
    - Pool recycle: 1 hour
    - Statement timeout: 30 seconds (database-enforced)
    - Lock timeout: 10 seconds
    - Isolation level: READ COMMITTED (not SERIALIZABLE)
    """
    
    # Connection pool settings
    url: str
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False
    
    # Transaction settings
    isolation_level: str = "READ_COMMITTED"
    autoflush: bool = False
    expire_on_commit: bool = False
    
    # Timeout settings (seconds)
    statement_timeout: int = 30
    lock_timeout: int = 10
    transaction_timeout: int = 60
    
    # Pool size limits
    max_connections: int = 100  # Total max including overflow
    min_connections: int = 5
    
    def __post_init__(self):
        """Validate configuration."""
        if self.pool_size < 1:
            raise ValueError("pool_size must be at least 1")
        if self.max_overflow < 0:
            raise ValueError("max_overflow cannot be negative")
        if self.isolation_level not in {"READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"}:
            raise ValueError(f"Invalid isolation_level: {self.isolation_level}")
        if self.statement_timeout < 1:
            raise ValueError("statement_timeout must be at least 1 second")
        if self.lock_timeout < 1:
            raise ValueError("lock_timeout must be at least 1 second")
        
        logger.info(
            f"DatabaseConfig validated (pool_size: {self.pool_size}, "
            f"max_overflow: {self.max_overflow}, "
            f"isolation: {self.isolation_level})"
        )
    
    def get_engine_options(self) -> dict:
        """Get SQLAlchemy engine options."""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "echo": self.echo,
            "connect_args": {
                "options": f"-c statement_timeout={self.statement_timeout}s "
                           f"-c lock_timeout={self.lock_timeout}s "
                           f"-c idle_in_transaction_session_timeout={self.transaction_timeout}s"
            },
        }
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create configuration from environment variables."""
        import os
        
        return cls(
            url=os.getenv("DATABASE_URL", "postgresql://localhost:5432/postgres"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            isolation_level=os.getenv("DB_ISOLATION_LEVEL", "READ_COMMITTED"),
            statement_timeout=int(os.getenv("DB_STATEMENT_TIMEOUT", "30")),
            lock_timeout=int(os.getenv("DB_LOCK_TIMEOUT", "10")),
            transaction_timeout=int(os.getenv("DB_TRANSACTION_TIMEOUT", "60")),
        )
