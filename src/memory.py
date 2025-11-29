#!/usr/bin/env python3
"""
Long-term Memory System using Chroma Vector Store
Stores and retrieves conversation history for context-aware responses
"""

from langchain.vectorstores import Chroma
from langchain.embeddings import OllamaEmbeddings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize embedder (same as codebase RAG)
embedder = OllamaEmbeddings(model="deepseek-coder-v2:16b-instruct-qat")

# Global conversation database
conversation_db = Chroma(persist_directory=".memory", embedding_function=embedder)


def save_memory(session_id: str, user_msg: str, ai_msg: str):
    """
    Save a conversation turn to memory
    
    Args:
        session_id: Unique session identifier
        user_msg: User's message
        ai_msg: AI's response
    """
    try:
        # Store both messages with metadata
        conversation_db.add_texts(
            [user_msg, ai_msg],
            metadatas=[
                {"session": session_id, "role": "user"},
                {"session": session_id, "role": "assistant"}
            ]
        )
        conversation_db.persist()
        logger.info(f"💾 Saved memory for session: {session_id}")
    except Exception as e:
        logger.error(f"Failed to save memory: {e}")


def get_memory(session_id: str, k=20):
    """
    Retrieve conversation history for a session
    
    Args:
        session_id: Unique session identifier
        k: Number of messages to retrieve (default: 20)
    
    Returns:
        String with formatted conversation history
    """
    try:
        # Search for messages from this session
        results = conversation_db.similarity_search(session_id, k=k)
        
        # Filter by session_id and format
        history = "\n".join([
            f"{r.page_content}" 
            for r in results 
            if r.metadata.get("session") == session_id
        ])
        
        logger.info(f"🔍 Retrieved {len(results)} memories for session: {session_id}")
        return history
    except Exception as e:
        logger.error(f"Failed to retrieve memory: {e}")
        return ""
