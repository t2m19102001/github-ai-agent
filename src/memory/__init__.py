"""
Memory Module
Long-term memory storage and retrieval for agents
"""

from .memory_manager import MemoryManager, MemoryEntry, ConversationContext

# Legacy imports for compatibility
try:
    from .memory_manager import save_memory, get_memory
except ImportError:
    pass

__all__ = ['MemoryManager', 'MemoryEntry', 'ConversationContext']
