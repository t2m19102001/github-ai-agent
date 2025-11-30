#!/usr/bin/env python3
"""
Long-term Memory System using Chroma Vector Store
Stores and retrieves conversation history for context-aware responses
Supports: Ollama (local), OpenAI (cloud), Groq (cloud with local fallback)
"""

from langchain_chroma import Chroma
from src.utils.logger import get_logger

# Import config
from src.config.settings import PROVIDER, MODELS, LLMProvider

logger = get_logger(__name__)

# Initialize embedder based on provider
def get_embedder():
    """Get embeddings model based on configured provider"""
    if PROVIDER == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(model=MODELS[PROVIDER])
        except Exception as e:
            logger.warning(f"⚠️ Ollama failed: {e}, using HuggingFace")
    
    # Fallback to free HuggingFace embeddings (for Groq/OpenAI/errors)
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except ImportError:
        raise ImportError("Install: pip install langchain-huggingface")

embedder = get_embedder()

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
