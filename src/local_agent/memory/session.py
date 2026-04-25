"""
Session Module.

Purpose: Manage session context and query history.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
import uuid


@dataclass
class QueryRecord:
    """A single query-response pair."""
    query_id: str
    query_text: str
    response_text: str
    retrieved_chunks: List[str]
    timestamp: datetime
    latency_ms: int
    tokens_used: int
    confidence: float


@dataclass
class SessionContext:
    """Complete session context."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    query_history: List[QueryRecord] = field(default_factory=list)
    retrieved_chunks: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    
    def add_query(self, query_text: str, response_text: str, retrieved_chunks: List[str], latency_ms: int, tokens_used: int, confidence: float) -> QueryRecord:
        """Record a new query-response pair."""
        record = QueryRecord(
            query_id=str(uuid.uuid4()),
            query_text=query_text,
            response_text=response_text,
            retrieved_chunks=retrieved_chunks,
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            confidence=confidence
        )
        self.query_history.append(record)
        return record
    
    def get_recent_context(self, n_queries: int = 3) -> str:
        """Get context from recent queries."""
        recent = self.query_history[-n_queries:] if self.query_history else []
        if not recent:
            return ""
        context_parts = []
        for record in recent:
            context_parts.append(f"Q: {record.query_text}")
            context_parts.append(f"A: {record.response_text[:200]}...")
        return "\n".join(context_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "query_count": len(self.query_history),
            "user_preferences": self.user_preferences,
        }
