#!/usr/bin/env python3
"""
Index codebase for RAG retrieval
Run this script to build the vector store index
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.codebase_rag import index_repo

if __name__ == "__main__":
    print("🚀 Starting codebase indexing...")
    print("📂 This will create a .chroma directory with the vector store")
    
    try:
        index_repo()
        print("✅ Indexing complete!")
        print("💡 You can now use RAG retrieval in CodeChatAgent")
    except Exception as e:
        print(f"❌ Error during indexing: {e}")
        sys.exit(1)
