#!/usr/bin/env python3
"""
Test script for long-term memory system
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory import save_memory, get_memory

def test_memory():
    """Test memory save and retrieval"""
    print("🧪 Testing Long-term Memory System...")
    
    # Test session
    session_id = "test-session-123"
    
    # Save some conversations
    print("\n💾 Saving conversations...")
    save_memory(session_id, "What is Python?", "Python is a high-level programming language.")
    save_memory(session_id, "How to use loops?", "Python has for and while loops.")
    save_memory(session_id, "Explain functions", "Functions are defined with 'def' keyword.")
    
    # Retrieve memory
    print("\n🔍 Retrieving memory...")
    memory = get_memory(session_id, k=10)
    
    print("\n📝 Retrieved Memory:")
    print("=" * 60)
    print(memory)
    print("=" * 60)
    
    if memory and len(memory) > 0:
        print("\n✅ Memory system working correctly!")
    else:
        print("\n❌ Memory system failed!")

if __name__ == "__main__":
    test_memory()
