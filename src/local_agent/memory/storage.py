"""
Storage Module.

Purpose: SQLite persistence for sessions and logs.
"""

class MemoryStorage:
    """Stores session data in SQLite."""
    
    def save_session(self, session):
        """Save session to storage."""
        raise NotImplementedError("P1-8: Memory storage not yet implemented")
    
    def load_session(self, session_id: str):
        """Load session from storage."""
        raise NotImplementedError("P1-8: Memory storage not yet implemented")
