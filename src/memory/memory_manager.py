#!/usr/bin/env python3
"""
Memory Manager Module
Provides long-term memory storage and retrieval for agents
"""

import os
import json
import sqlite3
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """Memory entry structure"""
    id: str
    key: str
    value: Any
    type: str  # fact, conversation, context, preference
    timestamp: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    importance: float = 1.0  # 0.0 to 1.0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ConversationContext:
    """Conversation context structure"""
    session_id: str
    user_id: str
    messages: List[Dict[str, Any]]
    summary: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MemoryManager:
    """Long-term memory management system"""
    
    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = db_path
        self.conn = None
        
        # Handle empty or invalid db_path
        if not db_path or db_path == "":
            # Default to data directory in project root
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            self.db_path = str(data_dir / "memory.db")
        
        self._initialize_database()
        
        logger.info(f"Initialized MemoryManager with database: {self.db_path}")
    
    def _initialize_database(self):
        """Initialize SQLite database for memory storage"""
        try:
            # Create data directory
            if self.db_path and self.db_path != "":
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            else:
                # Default to data directory in project root
                from pathlib import Path
                project_root = Path(__file__).parent.parent.parent
                data_dir = project_root / "data"
                data_dir.mkdir(exist_ok=True)
                self.db_path = str(data_dir / "memory.db")
            
            # Connect to database
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            
            # Create tables
            self._create_tables()
            
            logger.info("Memory database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing memory database: {e}")
            raise
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        # Memory entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                expires_at TEXT,
                metadata TEXT,
                importance REAL DEFAULT 1.0
            )
        """)
        
        # Conversation contexts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_contexts (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                messages TEXT NOT NULL,
                summary TEXT,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_key ON memory_entries(key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_timestamp ON memory_entries(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_user ON conversation_contexts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_contexts(session_id)")
        
        self.conn.commit()
    
    def remember(self, key: str, value: Any, memory_type: str = "fact",
                expires_in: Optional[timedelta] = None, 
                importance: float = 1.0, 
                metadata: Dict[str, Any] = None) -> str:
        """Store information in memory"""
        try:
            # Generate ID
            memory_id = f"mem_{int(datetime.now().timestamp() * 1000)}"
            
            # Calculate expiration
            expires_at = None
            if expires_in:
                expires_at = datetime.now() + expires_in
            
            # Store in database
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO memory_entries 
                (id, key, value, type, timestamp, expires_at, metadata, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id, key, json.dumps(value), memory_type,
                datetime.now().isoformat(),
                expires_at.isoformat() if expires_at else None,
                json.dumps(metadata or {}), importance
            ))
            
            self.conn.commit()
            
            logger.debug(f"Stored memory: {key} (type: {memory_type})")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise
    
    def recall(self, key: str, memory_type: str = None, 
               limit: int = 10) -> List[MemoryEntry]:
        """Retrieve information from memory"""
        try:
            cursor = self.conn.cursor()
            
            # Build query
            query = "SELECT * FROM memory_entries WHERE key = ?"
            params = [key]
            
            if memory_type:
                query += " AND type = ?"
                params.append(memory_type)
            
            # Add expiration filter
            query += " AND (expires_at IS NULL OR expires_at > ?)"
            params.append(datetime.now().isoformat())
            
            # Order by importance and timestamp
            query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to MemoryEntry objects
            entries = []
            for row in rows:
                entry = MemoryEntry(
                    id=row["id"],
                    key=row["key"],
                    value=json.loads(row["value"]),
                    type=row["type"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    importance=row["importance"]
                )
                entries.append(entry)
            
            logger.debug(f"Recalled {len(entries)} memories for key: {key}")
            return entries
            
        except Exception as e:
            logger.error(f"Error recalling memory: {e}")
            return []
    
    def search(self, query: str, memory_type: str = None, 
              limit: int = 10) -> List[MemoryEntry]:
        """Search memory by content"""
        try:
            cursor = self.conn.cursor()
            
            # Build search query
            search_query = f"%{query}%"
            sql_query = """
                SELECT * FROM memory_entries 
                WHERE (key LIKE ? OR value LIKE ?)
            """
            params = [search_query, search_query]
            
            if memory_type:
                sql_query += " AND type = ?"
                params.append(memory_type)
            
            # Add expiration filter
            sql_query += " AND (expires_at IS NULL OR expires_at > ?)"
            params.append(datetime.now().isoformat())
            
            # Order by relevance
            sql_query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()
            
            # Convert to MemoryEntry objects
            entries = []
            for row in rows:
                entry = MemoryEntry(
                    id=row["id"],
                    key=row["key"],
                    value=json.loads(row["value"]),
                    type=row["type"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    importance=row["importance"]
                )
                entries.append(entry)
            
            logger.debug(f"Found {len(entries)} memories for search: {query}")
            return entries
            
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []
    
    def forget(self, key: str = None, memory_id: str = None, 
                memory_type: str = None, older_than: timedelta = None) -> int:
        """Remove information from memory"""
        try:
            cursor = self.conn.cursor()
            
            # Build delete query
            conditions = []
            params = []
            
            if key:
                conditions.append("key = ?")
                params.append(key)
            
            if memory_id:
                conditions.append("id = ?")
                params.append(memory_id)
            
            if memory_type:
                conditions.append("type = ?")
                params.append(memory_type)
            
            if older_than:
                cutoff = datetime.now() - older_than
                conditions.append("timestamp < ?")
                params.append(cutoff.isoformat())
            
            if not conditions:
                logger.warning("No conditions provided for forget operation")
                return 0
            
            query = f"DELETE FROM memory_entries WHERE {' AND '.join(conditions)}"
            cursor.execute(query, params)
            
            deleted_count = cursor.rowcount
            self.conn.commit()
            
            logger.info(f"Forgot {deleted_count} memory entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error forgetting memory: {e}")
            return 0
    
    def save_conversation(self, session_id: str, user_id: str, 
                        messages: List[Dict[str, Any]], summary: str = None,
                        metadata: Dict[str, Any] = None) -> str:
        """Save conversation context"""
        try:
            # Serialize messages
            messages_json = json.dumps(messages)
            
            # Store in database
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO conversation_contexts 
                (session_id, user_id, messages, summary, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, messages_json, summary,
                datetime.now().isoformat(),
                json.dumps(metadata or {})
            ))
            
            self.conn.commit()
            
            logger.debug(f"Saved conversation context for session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            raise
    
    def get_conversation(self, session_id: str) -> Optional[ConversationContext]:
        """Retrieve conversation context"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_contexts 
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (session_id,))
            
            row = cursor.fetchone()
            if row:
                return ConversationContext(
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    messages=json.loads(row["messages"]),
                    summary=row["summary"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving conversation: {e}")
            return None
    
    def get_user_conversations(self, user_id: str, limit: int = 10) -> List[ConversationContext]:
        """Get all conversations for a user"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_contexts 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            conversations = []
            for row in rows:
                conv = ConversationContext(
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    messages=json.loads(row["messages"]),
                    summary=row["summary"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                conversations.append(conv)
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting user conversations: {e}")
            return []
    
    def cleanup_expired(self) -> int:
        """Clean up expired memory entries"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM memory_entries 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (datetime.now().isoformat(),))
            
            deleted_count = cursor.rowcount
            self.conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired memory entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired memories: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        try:
            cursor = self.conn.cursor()
            
            # Total memories
            cursor.execute("SELECT COUNT(*) as total FROM memory_entries")
            total_memories = cursor.fetchone()["total"]
            
            # Memories by type
            cursor.execute("""
                SELECT type, COUNT(*) as count 
                FROM memory_entries 
                GROUP BY type
            """)
            type_stats = {row["type"]: row["count"] for row in cursor.fetchall()}
            
            # Total conversations
            cursor.execute("SELECT COUNT(*) as total FROM conversation_contexts")
            total_conversations = cursor.fetchone()["total"]
            
            # Recent activity
            cursor.execute("""
                SELECT COUNT(*) as recent FROM memory_entries 
                WHERE timestamp > datetime('now', '-7 days')
            """)
            recent_memories = cursor.fetchone()["recent"]
            
            return {
                "total_memories": total_memories,
                "memories_by_type": type_stats,
                "total_conversations": total_conversations,
                "recent_memories": recent_memories,
                "database_path": self.db_path,
                "database_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {}
    
    def export_memory(self, file_path: str, memory_type: str = None) -> bool:
        """Export memory to JSON file"""
        try:
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM memory_entries"
            params = []
            
            if memory_type:
                query += " WHERE type = ?"
                params.append(memory_type)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            export_data = []
            for row in rows:
                export_data.append({
                    "id": row["id"],
                    "key": row["key"],
                    "value": json.loads(row["value"]),
                    "type": row["type"],
                    "timestamp": row["timestamp"],
                    "expires_at": row["expires_at"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "importance": row["importance"]
                })
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported {len(export_data)} memories to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting memory: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Memory database connection closed")


# Legacy functions for compatibility
def save_memory(key: str, value: Any, memory_type: str = "fact"):
    """Legacy save_memory function"""
    import os
    if not hasattr(save_memory, '_manager'):
        db_path = os.path.join("data", "memory.db")
        save_memory._manager = MemoryManager(db_path)
    return save_memory._manager.remember(key, value, memory_type)


def get_memory(key: str):
    """Legacy get_memory function"""
    import os
    if not hasattr(get_memory, '_manager'):
        db_path = os.path.join("data", "memory.db")
        get_memory._manager = MemoryManager(db_path)
    entries = get_memory._manager.recall(key)
    return entries[0].value if entries else None


# Global instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(db_path: str = "data/memory.db") -> MemoryManager:
    """Get global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(db_path)
    return _memory_manager


# Test function
def test_memory_manager(memory=None):
    """Test memory manager functionality"""
    try:
        # Create memory manager if not provided
        if memory is None:
            memory = MemoryManager("test_memory.db")
        
        # Test remember
        memory_id = memory.remember(
            key="user_preference",
            value={"theme": "dark", "language": "python"},
            memory_type="preference",
            importance=0.8
        )
        print(f"Stored memory with ID: {memory_id}")
        
        # Test recall
        entries = memory.recall("user_preference")
        print(f"Recalled {len(entries)} entries:")
        for entry in entries:
            print(f"  {entry.key}: {entry.value}")
        
        # Test search
        search_results = memory.search("preference")
        print(f"Search results: {len(search_results)} entries")
        
        # Test conversation
        session_id = memory.save_conversation(
            session_id="test_session",
            user_id="test_user",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            summary="Test conversation"
        )
        print(f"Saved conversation: {session_id}")
        
        # Test stats
        stats = memory.get_stats()
        print(f"Memory stats: {json.dumps(stats, indent=2, default=str)}")
        
        # Cleanup only if we created the memory manager
        if memory.db_path == "test_memory.db":
            memory.close()
            # Remove test database
            if os.path.exists("test_memory.db"):
                os.remove("test_memory.db")
        
    except Exception as e:
        print(f"Error testing memory manager: {e}")


if __name__ == "__main__":
    test_memory_manager()
