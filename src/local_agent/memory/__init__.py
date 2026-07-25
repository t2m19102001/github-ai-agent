"""
Memory Module.

Purpose: Session and log management.
Input: Agent actions
Output: Session context, logs

Components:
    session: Session context (query history)
"""

from src.local_agent.memory.session import SessionContext, QueryRecord
from src.local_agent.memory.storage import SessionStore, Turn

__all__ = ["QueryRecord", "SessionContext", "SessionStore", "Turn"]

# PostgresSessionStore is imported lazily by callers (src.local_agent.cli) to
# keep psycopg2 an optional dependency — importing this package must not require
# a Postgres driver to be installed.
