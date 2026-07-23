"""
Memory Module.

Purpose: Session and log management.
Input: Agent actions
Output: Session context, logs

Components:
    session: Session context (query history)
"""

from src.local_agent.memory.session import SessionContext, QueryRecord

__all__ = ["SessionContext", "QueryRecord"]
